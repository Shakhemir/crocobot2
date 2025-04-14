"""Разные вспомогательные утилиты"""

import re
import os
import pickle
import aiofiles
from telebot.types import Message, User
from src.game import Game
from src.config import TESTERS_IDS, bot_username, games, sync_bot
from src.config import logger, settings, set_chat_admin_commands
from app.words_generator import get_random_word
from app.statistics import inc_user_stat


def is_group_command(message: Message):
    if message.chat.type in ["group", "supergroup"]:
        if (
            message.reply_to_message
            and message.reply_to_message.from_user.username == bot_username
        ):
            return True
        if message.text.endswith(f"@{bot_username}"):
            return True


def is_group_message(message: Message):
    return message.chat.type in ["group", "supergroup"]


def is_admin_message(message: Message):
    if message.from_user.id in TESTERS_IDS and message.chat.type not in [
        "group",
        "supergroup",
    ]:
        return True


async def save_game(game: Game):
    async with aiofiles.open(
        f"{settings.STATE_SAVE_DIR}{game.game_chat_id}.pkl", "wb"
    ) as f:
        await f.write(pickle.dumps(game.save_state()))


def get_game_chat_id(message: Message | str) -> str:
    """Формирует chat_id для чата игры с учетом топиков и постов канала"""
    if isinstance(message, str):  # возвращает как есть
        return message
    if message.is_topic_message:  # чат топика
        return f"{message.chat.id}-{message.message_thread_id}"
    if message.message_thread_id is not None:
        # чат поста канала
        return f"{message.chat.id}-post-{message.message_thread_id}"
    return str(message.chat.id)  # обычный чат


async def get_game(message: Message | str, start_game: bool = None):
    chat_id = get_game_chat_id(message)
    game: Game = games.get(chat_id)
    if (
        game is None and start_game
    ):  # Если игра не найдена, а надо стартовать, то создаем
        game = Game(chat_id, message, get_random_word, save_game)
        games[chat_id] = game
        await save_game(game)
    elif start_game:
        game.define_chat_name(message)
        await save_game(game)
    return game


def log_error(msg: str):
    for tg_id in TESTERS_IDS:
        try:
            sync_bot.send_message(tg_id, msg)
        except:
            pass
        logger.error(msg)


async def load_game(
    filename: str, game_chat_id: str, chats_set_commands: set, **kwargs
) -> Game | None:
    """Загружает файл игры, если получается.
    Либо удаляет его если не актуальный или бот заблокирован в чате.
    Также делает попытку установить команды админам.
    """

    def remove_chat_file(chat_filename):
        print("removing...")
        os.remove(settings.STATE_SAVE_DIR + chat_filename)

    print(f"load_game: {filename=} {game_chat_id=} {len(chats_set_commands)=}")
    try:
        async with aiofiles.open(settings.STATE_SAVE_DIR + filename, "rb") as f:
            content = await f.read()
            state = pickle.loads(content)
            if (
                not state["active"]
                and game_chat_id != str(state["chat_id"])
                and not state["exclusive_timer"]
                and not state["used_words"]
            ):
                # В чате топика или поста не было игры, можно удалять
                return remove_chat_file(filename)

            chat_id = state["chat_id"]
            if chat_id not in chats_set_commands:
                if chat_available := await set_chat_admin_commands(state["chat_id"]):
                    chats_set_commands.add(chat_id)
                elif chat_available == -1:  # Чат не доступен, скорее всего заблокирован
                    return remove_chat_file(filename)

            # if chat_id in chats_set_commands:
            #     if state["active"] or state["exclusive_timer"]:
            restored_game = await Game.load_state(
                state,
                game_chat_id=game_chat_id,
                word_gen_func=get_random_word,
                save_game_func=save_game,
                **kwargs,
            )
            return restored_game
    except EOFError:
        log_error("Ошибка при загрузке файла %r" % filename)


async def load_games(**kwargs):
    loaded_game_states = {}
    chats_count = 0
    blocked_chats = 0
    chats_set = set()
    for filename_pkl in os.listdir(settings.STATE_SAVE_DIR):
        filename, ext = filename_pkl.split(".")
        if (
            ext == "pkl"
            and filename.startswith("-")
            and filename.replace("-", "").replace("post", "").isdigit()
        ):
            chat_id = filename
            restored_game = await load_game(filename_pkl, chat_id, chats_set, **kwargs)
            if restored_game is not None:
                chats_count += 1
                loaded_game_states[chat_id] = restored_game
            else:
                blocked_chats += 1
    print(f"{chats_count=}, {blocked_chats=}")
    return loaded_game_states


async def check_user_answer(message: Message, game: Game):
    """
    Проверка ответов пользователей в чате:

    :param message: текст сообщения и инфо о юзере
    :param game: текущая игра
    :return:
        -1 - повтор ответа, нужно удалить
        True - угадал слово
        None - не угадал
    """
    answer = message.text
    print("check_user_answer", answer, game.leader_name)
    user_answer = answer.lower().replace("ё", "е").replace("й", "и")
    if user_answer in game.answers_set:
        return -1

    normalized_current_word = re.sub(
        r"[^а-яa-z]+",
        " ",
        game.current_word.replace("ё", "е").replace("й", "и"),
        flags=re.IGNORECASE,
    )
    set_of_correct_words = set(word.lower() for word in normalized_current_word.split())
    normalized_user_answer = re.sub(
        r"[^а-яa-z]+", " ", user_answer, flags=re.IGNORECASE
    )
    set_of_words_in_message = set(word for word in normalized_user_answer.split())

    if not (set_of_correct_words - set_of_words_in_message):
        # Угадал слово
        await game.add_current_word_to_used(message.from_user)
        await inc_user_stat(game, message.from_user)  # Изменяем статистику
        return True
    game.answers_set.add(user_answer)  # Добавляем слово в список использованных


def log_game(text: str, game: Game, user: User | tuple):
    if isinstance(user, tuple):
        user_id, user_name = user
    else:
        user_id, user_name = user.id, user.full_name
    logger.info(
        "Chat=%s %r, user=%s %r, word=%r :: %s",
        game.chat_id,
        game.chat_title,
        user_id,
        user_name,
        game.current_word,
        text,
    )
