import asyncio
from telebot.types import Message
from src.config import bot, bot_title
import src.user_interface as ui
from src.game import Game
from src.utils import is_group_command, load_games, save_game
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
        await save_game(game)
    return game


@bot.message_handler(commands=["start"], func=is_group_command)
async def start_game(message: Message):
    """Старт игры"""
    chat_id = message.chat.id
    chat_game = await get_game(message)
    await chat_game.start_game(message, get_random_word, end_game)
    await save_game(chat_game)
    return await bot.send_message(
        chat_id, **ui.get_start_game_message(message.from_user.full_name)
    )


async def end_game(game):
    game.active = False
    game.game_timer = None
    await bot.send_message(game.chat_id, **ui.get_end_game_message())
    await save_game(game)


@bot.message_handler(commands=["check"], func=is_group_command)
async def check_game(message: Message):
    """Тестируем"""
    chat_game = await get_game(message)
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


async def start_bot():
    global games
    games = await load_games(end_game_func=end_game)
    print(f"{games=}")
    await bot.infinity_polling()


if __name__ == "__main__":
    asyncio.run(start_bot())
