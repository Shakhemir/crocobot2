import os.path
import aiofiles
import json
from telebot.types import User
from src.game import Game
from src.settings import settings


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
    return stats


async def save_stats(file_name, stats: dict) -> None:
    async with aiofiles.open(file_name, "w", encoding="utf-8") as f:
        await f.write(json.dumps(stats, indent=4, ensure_ascii=False))


def get_chat_stats_filename(chat_id) -> str:
    """Возвращает путь к файлу статистики чата"""
    file_name = os.path.join(
        settings.CHATS_STATS_DIR, str(chat_id).lstrip("-"), "stats.json"
    )
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
    chat_filename = get_chat_stats_filename(game.chat_id)
    await inc_user_stat_in_file(chat_filename, user)

    # Увеличиваем очки пользователя в глобальной статистике
    await inc_user_stat_in_file(settings.GLOBAL_STATS_FILE, user)


async def inc_user_fine(game: Game):
    """Увеличиваем штраф пользователя, когда он не взял ведущего"""

    if game.current_leader == game.exclusive_user:
        return  # Все нормально, не штрафуем

    chat_filename = get_chat_stats_filename(game.chat_id)
    stats = await load_stats(chat_filename)  # Загружаем статистику чата
    user_id = str(game.exclusive_user)
    user_stat = stats.get(user_id, {})

    # Смотрим сколько раз нарушил
    is_fined = False
    user_stat["faults"] = user_stat.get("faults", 0) + 1
    if user_stat["faults"] >= settings.FAULT_SIZE:
        # Штрафуем
        del user_stat["faults"]
        user_stat["fines"] = user_stat.get("fines", 0) + 1
        is_fined = True

    stats.update({user_id: user_stat})
    await save_stats(chat_filename, stats)  # Сохраняем статистику
    return is_fined


def get_correct_word_form(count):
    if count % 10 == 1 and count % 100 != 11:
        return "ответ"
    elif 2 <= count % 10 <= 4 and not (12 <= count % 100 <= 14):
        return "ответа"
    else:
        return "ответов"


async def get_global_stats():
    """Возвращает глобальную статистику игроков"""

    global_stats = await load_stats(settings.GLOBAL_STATS_FILE)
    sorted_stats = sorted(
        global_stats.items(), key=lambda x: x[1]["score"], reverse=True
    )
    top_players = sorted_stats[:30]
    if not top_players:
        return dict(text="Пока нет глобальной статистики.")
    result_message = "🌐 🏆 <b>Глобальный ТОП игроков в крокодила 🐊</b>\n\n"
    for idx, (user_id_str, data) in enumerate(top_players, start=1):
        user_name = data["name"]
        score = data["score"]
        word = get_correct_word_form(score)
        result_message += f"{idx}. {user_name} — {score} {word}\n"
    result_message += "\nНаш чат для игры в крокодил @game_public_chat. Присоединяйтесь к нам!"
    return dict(text=result_message, parse_mode="HTML")


async def get_chat_stats(chat_id):
    """Возвращает статистику игроков в текущем чате"""

    chat_filename = get_chat_stats_filename(chat_id)
    chat_stats = await load_stats(chat_filename)
    if not chat_stats:
        return dict(text="Пока нет статистики для этого чата.")
    sorted_stats = sorted(chat_stats.items(), key=lambda x: x[1]["score"], reverse=True)
    top_players = sorted_stats[:20]
    result_message = "🏆 <b>Топ игроков в крокодила 🐊 в этом чате</b>\n\n"
    for idx, (user_id_str, data) in enumerate(top_players, start=1):
        user_name = data["name"]
        fines = data.get("fines", 0)  # Штрафы
        score = data["score"] - fines
        word = get_correct_word_form(score)
        result_message += f"{idx}. {user_name} — {score} {word}\n"
    result_message += "\nНаш чат для игры в крокодил @game_public_chat. Присоединяйтесь к нам!"
    return dict(text=result_message, parse_mode="HTML")
