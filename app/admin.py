from pathlib import Path
from telebot.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from src.config import bot, games, settings
from src.utils import is_admin_message, is_group_command, get_game


@bot.message_handler(commands=["chats"], func=is_admin_message)
async def get_chats_for_admins(message: Message):
    """Список активных чатов:"""
    await bot.send_message(message.chat.id, **make_active_chats_markup())


sorted_chat_files = []  # Список чатов, сортированный по времени
CHATS_IN_PAGE = settings.CHAT_PAGE_SIZE


def get_sorted_chat_files():
    """Готовим отсортированный список чатов"""

    def check_file(f: Path) -> bool:
        return f.is_file() and f.suffix == ".pkl" and f.stem.startswith("-")

    global sorted_chat_files
    folder = Path(settings.STATE_SAVE_DIR)
    sorted_files = sorted(
        folder.iterdir(),
        key=lambda f: f.stat().st_mtime if check_file(f) else 0,
        reverse=True,
    )
    sorted_chat_files = [f.stem for f in sorted_files]


def make_active_chats_markup(offset=0, refresh_list=False):
    if not sorted_chat_files or refresh_list:
        get_sorted_chat_files()
    chats_markup = InlineKeyboardMarkup()
    print(get_chats_for_admins.__doc__)
    if offset < 0:
        offset = 0
    for chat_id in sorted_chat_files[offset : offset + CHATS_IN_PAGE]:
        game = games.get(chat_id)
        if game is None:
            continue
        prefix = "🟢" if game.active else "🔴"
        chat_btn = InlineKeyboardButton(
            f"{prefix} {game.chat_title}", callback_data=f"chat_info{game.chat_id}"
        )
        chats_markup.add(chat_btn)

    # Кнопки пагинации
    page_buttons = []
    if offset:
        page_buttons += [
            InlineKeyboardButton("⇤", callback_data=f"chats:0"),
            InlineKeyboardButton("<", callback_data=f"chats:{offset - CHATS_IN_PAGE}"),
        ]
    page_buttons.append(
        InlineKeyboardButton("🔄", callback_data=f"refresh_chats:{offset}")
    )
    last_offset = (len(sorted_chat_files) // CHATS_IN_PAGE) * CHATS_IN_PAGE
    is_last_page = offset + CHATS_IN_PAGE >= len(sorted_chat_files)
    if not is_last_page:
        page_buttons += [
            InlineKeyboardButton(">", callback_data=f"chats:{offset + CHATS_IN_PAGE}"),
            InlineKeyboardButton("⇥", callback_data=f"chats:{last_offset}"),
        ]

    chats_markup.add(*page_buttons, row_width=5)
    all_pages = (len(sorted_chat_files) - 1 + CHATS_IN_PAGE) // CHATS_IN_PAGE
    page = offset // CHATS_IN_PAGE + 1
    text = (
        f"<b>{get_chats_for_admins.__doc__}</b>\n\n"
        f"Всего чатов: <code>{len(sorted_chat_files)}</code>\n"
        f"Страница: <code>{page} / {all_pages}</code>"
    )
    return dict(text=text, parse_mode="html", reply_markup=chats_markup)


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


@bot.message_handler(content_types=["text"], func=is_admin_message)
async def admins_messages(message: Message):
    if message.text.startswith("-") and message.text[1:].isdigit():
        chat_id = message.text
        game_stats = await make_tester_game_stats(chat_id)
        await bot.send_message(chat_id=message.chat.id, **game_stats)
    elif message.reply_to_message:
        # Подкидывание слов админом
        find_word_idx = '"chat_id":'
        start_index = message.reply_to_message.text.find(find_word_idx)
        end_index = message.reply_to_message.text.find(",", start_index)
        chat_id = message.reply_to_message.text[
            start_index + len(find_word_idx) : end_index
        ]
        await bot.delete_message(message.chat.id, message.message_id)
        game = games.get(chat_id)
        game.next_words.append(message.text)
        game_stats = await make_tester_game_stats(chat_id)
        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.reply_to_message.message_id,
            **game_stats,
        )


async def make_tester_game_stats(chat_id: str):
    chat_game = await get_game(chat_id)
    markup = InlineKeyboardMarkup()
    refresh_btn = InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh{chat_id}")
    close_btn = InlineKeyboardButton("✖️", callback_data="close")
    markup.add(refresh_btn, close_btn)
    return dict(text=str(chat_game), reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("chat_info"))
async def chat_info_callback_handler(call: CallbackQuery):
    chat_id = call.data.lstrip("chat_info")
    game_stats = await make_tester_game_stats(chat_id)
    await bot.send_message(call.message.chat.id, **game_stats)


@bot.callback_query_handler(func=lambda call: call.data.startswith("chats:"))
async def chat_info_callback_handler(call: CallbackQuery):
    offset = int(call.data.split(":")[1])
    kwargs = make_active_chats_markup(offset=offset)
    await bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        **kwargs,
    )


@bot.callback_query_handler(func=lambda call: call.data == "close")
async def close_callback_handler(call: CallbackQuery):
    await bot.delete_message(
        chat_id=call.message.chat.id, message_id=call.message.message_id
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("refresh"))
async def chat_info_refresh_callback_handler(call: CallbackQuery):
    if "chats" in call.data:
        offset = int(call.data.split(":")[1])
        kwargs = make_active_chats_markup(offset=offset, refresh_list=True)
    else:
        chat_id = call.data.lstrip("refresh")
        kwargs = await make_tester_game_stats(chat_id)
    try:
        await bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            **kwargs,
        )
    except:
        await bot.answer_callback_query(call.id)
