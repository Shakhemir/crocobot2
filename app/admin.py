from telebot.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from src.config import bot, games
from src.utils import is_admin_message, is_group_command, get_game


@bot.message_handler(commands=["chats"], func=is_admin_message)
async def get_chats_for_admins(message: Message):
    """Список активных чатов:"""
    chats_markup = InlineKeyboardMarkup()
    print(get_chats_for_admins.__doc__)
    for game in games.values():
        print(game)
        if game.active:
            chat_btn = InlineKeyboardButton(
                game.chat_title, callback_data=f"chat_info{game.chat_id}"
            )
            chats_markup.add(chat_btn)
    await bot.send_message(
        message.chat.id, get_chats_for_admins.__doc__, reply_markup=chats_markup
    )


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


async def make_tester_game_stats(chat_id):
    chat_game = await get_game(chat_id)
    markup = InlineKeyboardMarkup()
    button = InlineKeyboardButton("Обновить", callback_data=f"refresh{chat_id}")
    markup.add(button)
    return dict(text=str(chat_game), reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("chat_info"))
async def chat_info_callback_handler(call: CallbackQuery):
    chat_id = int(call.data.lstrip("chat_info"))
    kwargs = await make_tester_game_stats(chat_id)
    await bot.send_message(call.message.chat.id, **kwargs)


@bot.callback_query_handler(func=lambda call: call.data.startswith("refresh"))
async def chat_info_refresh_callback_handler(call: CallbackQuery):
    chat_id = int(call.data.lstrip("refresh"))
    kwargs = await make_tester_game_stats(chat_id)
    try:
        await bot.edit_message_text(
            chat_id=call.message.chat.id, message_id=call.message.message_id, **kwargs
        )
    except:
        await bot.answer_callback_query(call.id)
