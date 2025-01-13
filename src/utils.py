"""Разные вспомоганательные утилиты"""

import asyncio
import os
import pickle
import aiofiles
from src.game import Game
from src.config import bot, bot_username
from src.config import logger, settings


def is_group_command(message):
    return message.chat.type in ["group", "supergroup"] and message.text.endswith(
        f"@{bot_username}"
    )


async def save_game(game: Game):
    async with aiofiles.open(f"{settings.STATE_SAVE_DIR}{game.chat_id}.pkl", "wb") as f:
        await f.write(pickle.dumps(game.save_state()))


async def load_games(**kwargs):
    loaded_game_states = {}
    for filename_pkl in os.listdir(settings.STATE_SAVE_DIR):
        filename, ext = filename_pkl.split(".")
        if ext == "pkl" and filename.startswith("-") and filename[1:].isdigit():
            chat_id = int(filename)
            try:
                async with aiofiles.open(
                    settings.STATE_SAVE_DIR + filename_pkl, "rb"
                ) as f:
                    content = await f.read()
                    state = pickle.loads(content)
                    restored_game = await Game.load_state(state, **kwargs)
            except EOFError:
                logger.error("Ошибка при загрузке файла %r", filename_pkl)
            else:
                loaded_game_states[chat_id] = restored_game

    return loaded_game_states
