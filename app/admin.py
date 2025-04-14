from pathlib import Path
from telebot.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telebot.apihelper import ApiTelegramException
from telebot import util
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
        if game.active:
            prefix = "🟢"
        elif game.used_words:
            prefix = "🔴"
        else:
            prefix = "⚫️"
        if game.chat_username:
            prefix = "🔗 " + prefix
        chat_title = (
            f"{game.chat_title} / {game.topic_name}"
            if game.topic_id
            else game.chat_title
        )
        if "post" in game.game_chat_id:
            chat_title += " post" + game.game_chat_id.split("post")[1]
        chat_btn = InlineKeyboardButton(
            f"{prefix} {chat_title}", callback_data=f"chat_info{game.game_chat_id}"
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
    """
    Информация об игре чата.
    """
    chat_game = await get_game(chat_id)
    markup = InlineKeyboardMarkup()
    refresh_btn = InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh{chat_id}")
    tg_chat_btn = InlineKeyboardButton("…", callback_data=f"tg_chat_info{chat_id}")
    close_btn = InlineKeyboardButton("✖️", callback_data="close")
    markup.add(refresh_btn, tg_chat_btn, close_btn)
    active = "🟢" if chat_game.active else "🔴"
    chat_info = util.escape(str(chat_game))
    chat_title = util.escape(chat_game.chat_title)
    text = f"{active} <b>{chat_title}</b>\n{chat_info}"
    return dict(text=text, reply_markup=markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data.startswith("chat_info"))
async def chat_info_callback_handler(call: CallbackQuery):
    chat_id = call.data.lstrip("chat_info")
    game_stats = await make_tester_game_stats(chat_id)
    await bot.send_message(call.message.chat.id, **game_stats)


async def get_tg_chat_info(chat_id: str):
    """
    Информация о чате.
    """
    markup = InlineKeyboardMarkup()
    close_btn = InlineKeyboardButton("✖️", callback_data="close")
    markup.add(close_btn)
    chat = await bot.get_chat(chat_id)
    username = "@" + chat.username if chat.username else ""
    chat_title = util.escape(chat.title)
    chat_description = "\n" + util.escape(chat.description) if chat.description else ""
    invite_link = chat.invite_link if chat.invite_link else ""
    pinned_message = ""
    if chat.pinned_message:
        pin = (
            util.escape(chat.pinned_message.text)
            if chat.pinned_message.content_type == "text"
            else chat.pinned_message.content_type
        )
        pinned_message = "\nPinned: " + pin
    try:
        admins = await bot.get_chat_administrators(chat_id)
    except ApiTelegramException as e:
        members_info = str(e)
    else:
        creator = None
        for admin in admins:
            if admin.status == "creator":
                creator = admin
        creator_username = "@" + creator.user.username if creator.user.username else ""
        members_count = await bot.get_chat_member_count(chat_id)
        members_info = f"Creator: {creator_username} <code>{util.escape(creator.user.full_name)}</code>\n"
        f"Admins count: <code>{len(admins)}</code>\n"
        f"Members count: <code>{members_count}</code>\n"
    text = (
        f"{username} <b>{chat_title}</b>\n<i>{chat.type}</i>{chat_description}\n"
        f"{invite_link}{pinned_message}\n\n{members_info}"
    )
    return dict(text=text, reply_markup=markup, parse_mode="html")


@bot.callback_query_handler(func=lambda call: call.data.startswith("tg_chat_info"))
async def tg_chat_info_callback_handler(call: CallbackQuery):
    chat_id = call.data.lstrip("tg_chat_info")
    tg_chat_info = await get_tg_chat_info(chat_id)
    await bot.send_message(call.message.chat.id, **tg_chat_info)


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
