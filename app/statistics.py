import os.path
import aiofiles
import json
from telebot.types import User
from src.game import Game
from src.settings import settings

CHATS_DIR = settings.CHATS_STATS_DIR


async def load_stats(file_path) -> dict:
    """Загружает статистику из JSON файла, заодно делаем проверки на существования пути к файлу"""

    # Проверяем, если не существует нужная папка и создаем ее
    dir_name, file_name = os.path.split(file_path)
    if dir_name and not os.path.exists(dir_name):
        # Проверяем вдруг папка под старым именем, где "-" вначале
        left_part, chat_part = os.path.split(dir_name)
        if os.path.exists(old_path := os.path.join(left_part, "-" + chat_part)):
            # Переименовываем папку чата, где начинается с "-"
            os.rename(old_path, os.path.join(left_part, chat_part))
        else:
            # Иначе создаем новую папку
            os.makedirs(dir_name)

    # Если не существует файла статистики, то возвращаем пустой словарь
    if not os.path.exists(file_path):
        return {}

    async with aiofiles.open(file_path, encoding="utf-8") as f:
        content = await f.read()
    stats = json.loads(content)
    print(stats)
    return stats


async def save_stats(file_name, stats: dict) -> None:
    async with aiofiles.open(file_name, "w", encoding="utf-8") as f:
        await f.write(json.dumps(stats, indent=4, ensure_ascii=False))


def get_chat_stats_filename(game: Game) -> str:
    """Возвращает путь к файлу статистики чата"""
    file_name = os.path.join(CHATS_DIR, str(game.chat_id).lstrip("-"), "stats.json")
    return file_name


async def inc_user_stat_in_file(file_name, user: User):
    """Увеличивает очки пользователя в конкретном файле статистики"""

    stats = await load_stats(file_name)  # Загружаем статистику

    # Увеличиваем очки пользователя
    user_id = str(user.id)
    user_stat = stats.get(user_id, {})
    if not user_stat:
        user_stat["score"] = 1
    else:
        user_stat["score"] += 1
    user_stat["name"] = user.full_name
    stats.update({user_id: user_stat})

    await save_stats(file_name, stats)  # Сохраняем статистику


async def inc_user_stat(game: Game, user: User):
    """Увеличиваем очки пользователю и записываем в глобальную статистику и в статистику чата"""

    # Увеличиваем очки пользователя в чате
    chat_filename = get_chat_stats_filename(game)
    await inc_user_stat_in_file(chat_filename, user)

    # Увеличиваем очки пользователя в глобальной статистике
    await inc_user_stat_in_file(settings.GLOBAL_STATS_FILE, user)
