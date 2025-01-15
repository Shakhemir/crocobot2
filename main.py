import asyncio
from telebot.types import Message, CallbackQuery
from src.config import bot, bot_title
import src.user_interface as ui
from src.game import Game
from src.utils import (
    is_group_command,
    is_group_message,
    load_games,
    save_game,
    check_user_answer,
)
from app.words_generator import get_random_word
from app.statistics import inc_user_stat, get_global_stats, get_chat_stats


games: dict  # Словарь с активными играми в чатах


@bot.message_handler(
    commands=["start"],
    func=lambda message: message.chat.type not in ["group", "supergroup"],
)
async def start_game(message: Message):
    """Старт в приватном чате"""
    return await bot.reply_to(message, **ui.get_welcome_message(bot_title))


async def get_game(message: Message):
    game = games.get(message.chat.id)
    if game is None:
        game = Game(message, get_random_word, save_game)
        games[message.chat.id] = game
        await save_game(game)
    return game


@bot.message_handler(commands=["start"], func=is_group_command)
async def start_game(message: Message):
    """Старт игры"""
    chat_id = message.chat.id
    chat_game = await get_game(message)
    if chat_game:  # Если игра уже активна
        return await bot.send_message(chat_id, **ui.get_game_already_started_message())
    await chat_game.start_game(message.from_user, end_game)
    return await bot.send_message(
        chat_id, **ui.get_start_game_message(message.from_user.full_name)
    )


@bot.message_handler(commands=["stats_global"])
async def stats_global(message: Message):
    """Общая статистика игры"""
    result = await get_global_stats()
    return await bot.send_message(message.chat.id, **result)


@bot.message_handler(commands=["stats"], func=is_group_command)
async def stats(message: Message):
    """Статистика игры по чату"""
    result = await get_chat_stats(message.chat.id)
    return await bot.send_message(message.chat.id, **result)


async def end_game(game):
    """Отправляем сообщение об окончании игры"""
    await bot.send_message(game.chat_id, **ui.get_end_game_message())


@bot.message_handler(commands=["check"], func=is_group_command)
async def check_game(message: Message):
    """Тестируем"""
    chat_game = await get_game(message)
    print("check_game", chat_game)
    active = "🟢" if chat_game.active else "🔴"
    if gt := chat_game.game_timer:
        interval, time_left, time_remain = gt.interval, gt.time_left, gt.time_remain
        gt_text = f"{interval}s: {time_left}s, {time_remain}s"
    else:
        gt_text = "No game timer"
    return await bot.send_message(
        message.chat.id,
        f"{active} {gt_text}\nСлово: {chat_game.current_word}\n"
        f"{chat_game.used_words=}",
    )


@bot.message_handler(content_types=["text"], func=is_group_message)
async def chat_messages(message: Message):
    """Обработчик сообщений в чатах"""
    chat_id = message.chat.id
    print("chat_messages", message.text)
    chat_game = await get_game(message)

    # Если игра не активна либо пишет ведущий, то выходим
    if not chat_game or message.from_user.id == chat_game.current_leader:
        return
    result = await check_user_answer(message, chat_game)  # Проверяем ответ из чата
    if result == -1:  # Повторный ответ
        try:
            await bot.delete_message(chat_id, message.message_id)
        except:
            pass
    elif result:  # Угадал слово
        await inc_user_stat(chat_game, message.from_user)  # Изменяем статистику
        await bot.send_message(
            chat_id,
            **ui.get_new_game_message(message.from_user, chat_game.current_word),
        )


@bot.callback_query_handler(func=lambda call: True)
async def callback_handler(call: CallbackQuery):
    chat_id = call.message.chat.id
    chat_game = await get_game(call.message)
    if call.data == "want_to_lead" and not chat_game:
        if chat_game.exclusive_user and call.from_user.id != chat_game.exclusive_user:
            time_remain = chat_game.exclusive_timer.time_remain
            return await bot.answer_callback_query(
                call.id,
                f"Вы станете ведущим, если отгадавший не займет эту роль в течение {time_remain} секунд",
                show_alert=True,
            )
        await chat_game.start_game(call.from_user, end_game)
        await bot.answer_callback_query(
            call.id, text=f"Ваше слово: {chat_game.current_word}", show_alert=True
        )
        await bot.send_message(
            chat_id, **ui.get_lead_game_message(call.from_user.full_name)
        )
    elif call.data == "view_word" and call.from_user.id == chat_game.current_leader:
        await bot.answer_callback_query(
            call.id, text=f"Ваше слово: {chat_game.current_word}", show_alert=True
        )
    elif call.data == "change_word" and call.from_user.id == chat_game.current_leader:
        chat_game.define_new_word()
        await bot.answer_callback_query(
            call.id, text=f"Ваше новое слово: {chat_game.current_word}", show_alert=True
        )
    elif call.from_user.id != chat_game.current_leader:
        await bot.answer_callback_query(call.id, text="Вы не ведущий", show_alert=True)
    else:
        await bot.answer_callback_query(call.id)


async def start_bot():
    global games
    games = await load_games(
        word_gen_func=get_random_word, save_game_func=save_game, end_game_func=end_game
    )
    print(f"{games=}")
    await bot.infinity_polling()


if __name__ == "__main__":
    asyncio.run(start_bot())
