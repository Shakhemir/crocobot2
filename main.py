import asyncio

from telebot.types import Message
from src.config import bot, bot_username, bot_title
import src.user_interface as ui
from src.game import Game
from app.words_generator import get_random_word


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
        game = Game(message)
        games[message.chat.id] = game
        await save_games()
    return game


async def save_games():
    await bot.set_common_data(games=games)


def is_group_command(message):
    return message.chat.type in ["group", "supergroup"] and message.text.endswith(
        f"@{bot_username}"
    )


@bot.message_handler(commands=["start"], func=is_group_command)
async def start_game(message: Message):
    """Старт игры"""
    chat_id = message.chat.id
    chat_game = await get_game(message)
    await chat_game.start_game(bot, message, get_random_word)
    return await bot.send_message(
        chat_id, **ui.get_start_game_message(message.from_user.full_name)
    )


@bot.message_handler(commands=["check"], func=is_group_command)
async def check_game(message: Message):
    """Тестируем"""
    chat_game = await get_game(message)
    gt = chat_game.game_timer
    interval, time_left, time_remain = gt.interval, gt.time_left, gt.time_remain
    return await bot.send_message(
        message.chat.id, f"{interval}s: {time_left}s, {time_remain}s\n"
                         f"Слово: {chat_game.current_word}\n"
                         f"{chat_game.used_words=}"
    )


async def start_bot():
    global games
    games = await bot.get_common_data("games")
    games = games or {}
    await bot.infinity_polling()


if __name__ == "__main__":
    asyncio.run(start_bot())
