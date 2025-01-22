"""Разные вспомоганательные утилиты"""

import re
import os
import pickle
import aiofiles
from telebot.types import Message, User
from src.game import Game
from src.config import TESTERS_IDS, bot_username, games
from src.config import logger, settings
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
    file_name = (
        game.chat_id if game.topic_id is None else f"{game.chat_id}-{game.topic_id}"
    )
    async with aiofiles.open(f"{settings.STATE_SAVE_DIR}{file_name}.pkl", "wb") as f:
        await f.write(pickle.dumps(game.save_state()))


async def get_game(message: Message | str):
    chat_id: str = (
        message
        if isinstance(message, str)
        else (
            str(message.chat.id)
            if not message.is_topic_message
            else f"{message.message_thread_id}-{message.message_thread_id}"
        )
    )
    game = games.get(chat_id)
    if game is None:
        game = Game(message, get_random_word, save_game)
        games[chat_id] = game
        await save_game(game)
    return game


async def load_games(**kwargs):
    loaded_game_states = {}
    for filename_pkl in os.listdir(settings.STATE_SAVE_DIR):
        filename, ext = filename_pkl.split(".")
        if ext == "pkl" and filename.startswith("-") and filename[1:].isdigit():
            chat_id = filename
            try:
                async with aiofiles.open(
                    settings.STATE_SAVE_DIR + filename_pkl, "rb"
                ) as f:
                    content = await f.read()
                    state = pickle.loads(content)
                    restored_game = await Game.load_state(
                        state,
                        word_gen_func=get_random_word,
                        save_game_func=save_game,
                        **kwargs,
                    )
            except EOFError:
                logger.error("Ошибка при загрузке файла %r", filename_pkl)
            else:
                loaded_game_states[chat_id] = restored_game

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
    game.answers_set.add(user_answer)

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
