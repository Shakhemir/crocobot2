"""
Общие конфиги
"""

import asyncio
import logging.handlers
from telebot.asyncio_storage import StatePickleStorage
from telebot.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeChat,
    BotCommandScopeAllPrivateChats,
)
from src.my_telebot import MyTeleBot
from .settings import settings

TESTERS_IDS = tuple(map(int, settings.TESTERS_IDS.split(",")))
print(f"{TESTERS_IDS=}")

games = {}  # Словарь с активными играми в чатах


async def init_telegram_bot():
    bot = MyTeleBot(
        settings.BOT_TOKEN, tester_ids=TESTERS_IDS, state_storage=StatePickleStorage()
    )
    await bot.init_common_sate()
    get_me = await bot.get_me()
    bot_username = get_me.username
    bot_title = get_me.full_name
    await bot.set_my_commands(
        [
            BotCommand("start", "Начало"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
    )
    await bot.set_my_commands(
        [
            BotCommand("start", "Начало игры"),
            # BotCommand("check", "Тесты"),
            BotCommand("stats", "Статистика по чату"),
            BotCommand("stats_global", "Глобальная статистика"),
        ],
        scope=BotCommandScopeAllGroupChats(),
    )
    for tester_id in TESTERS_IDS:
        await bot.set_my_commands(
            [
                BotCommand("start", "Начало"),
                BotCommand("chats", "Активные чаты"),
                BotCommand("admin", "Команды админа"),
            ],
            scope=BotCommandScopeChat(tester_id),
        )
    return bot, bot_username, bot_title


bot, bot_username, bot_title = asyncio.run(init_telegram_bot())


def get_logger():
    # Настройка логирования
    file_handler = logging.handlers.RotatingFileHandler(
        settings.LOG_FILE, maxBytes=1024 * 1024, backupCount=10, encoding="utf-8"
    )
    file_formatter = logging.Formatter("%(asctime)s :: %(message)s")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(settings.LOG_LEVEL)
    logger = logging.getLogger(__name__)
    logger.setLevel(settings.LOG_LEVEL)
    logger.addHandler(file_handler)
    logger.info("Start")

    return logger


logger = get_logger()
