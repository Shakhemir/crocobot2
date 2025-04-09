"""
Общие конфиги
"""

import asyncio
import logging.handlers
from telebot import TeleBot
from telebot.asyncio_storage import StatePickleStorage
from telebot.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeChat,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChatAdministrators,
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
    sync_bot = TeleBot(settings.BOT_TOKEN)
    await bot.init_common_sate()
    get_me = await bot.get_me()
    bot_username = get_me.username
    bot_title = get_me.full_name
    print(f"@{bot_username} {bot_title}")
    await bot.set_my_commands(
        [
            BotCommand("start", "Начало"),
        ],
        scope=BotCommandScopeAllPrivateChats(),
    )
    await bot.set_my_commands(
        [
            BotCommand("start", "Начало игры"),
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
    return bot, bot_username, bot_title, sync_bot


bot, bot_username, bot_title, sync_bot = asyncio.run(init_telegram_bot())


async def set_chat_admin_commands(chat_id):
    try:
        await bot.set_my_commands(
            [
                BotCommand("start", "Начало игры"),
                BotCommand("stop", "Остановить игру"),
                BotCommand("stats", "Статистика по чату"),
                BotCommand("stats_global", "Глобальная статистика"),
            ],
            scope=BotCommandScopeChatAdministrators(chat_id=chat_id),
        )
    except Exception:
        pass


def get_logger():
    # Настройка логирования
    file_handler = logging.handlers.RotatingFileHandler(
        settings.LOG_FILE, maxBytes=1024 * 1024, backupCount=10, encoding="utf-8"
    )
    file_formatter = logging.Formatter("%(asctime)s :: %(message)s")
    file_handler.setFormatter(file_formatter)
    logger = logging.getLogger(__name__)
    logger.setLevel(settings.LOG_LEVEL)
    logger.addHandler(file_handler)
    logger.info("Start")

    return logger


logger = get_logger()
