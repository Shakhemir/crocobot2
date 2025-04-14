import asyncio
from telebot.types import Message, CallbackQuery
from src.config import bot, bot_title, games, TESTERS_IDS
import src.user_interface as ui
from src.utils import (
    is_group_command,
    is_group_message,
    load_games,
    check_user_answer,
    log_game,
)
from src.game import Game
from app.statistics import get_global_stats, get_chat_stats, inc_user_fine
import app.admin  # don't remove


@bot.message_handler(
    commands=["start"],
    func=lambda message: message.chat.type not in ["group", "supergroup"],
)
async def start_command(message: Message):
    """Старт в приватном чате"""
    return await bot.reply_to(message, **ui.get_welcome_message(bot_title))


@bot.message_handler(commands=["start"], func=is_group_command)
async def start_command(message: Message):
    """Старт игры"""
    chat_id = message.chat.id
    chat_game = await Game.get_game(message, start_game=True)
    if chat_game:  # Если игра уже активна
        return await bot.send_message(
            chat_id, **ui.get_game_already_started_message(), **chat_game.msg_kwargs
        )
    await start_game(chat_game, chat_id, message.from_user)
    game_time = (chat_game.game_timer.interval + 29) // 60
    log_game("Игра началась", chat_game, message.from_user)
    return await bot.send_message(
        chat_id,
        **ui.get_start_game_message(message.from_user, game_time),
        **chat_game.msg_kwargs,
    )


@bot.message_handler(commands=["stop"], func=is_group_command)
async def stop_command(message: Message):
    """Стоп игры – команда для администраторов чата"""
    print("stop_command")
    chat_id = message.chat.id
    print(chat_id)
    print(message.from_user.id, message.from_user.username, message.from_user.full_name)
    chat_member = await bot.get_chat_member(chat_id, message.from_user.id)
    print(chat_member.status)
    if (
        chat_member.status in ("creator", "administrator")
        or message.from_user.username == "GroupAnonymousBot"
    ):
        chat_game = await Game.get_game(message)
        if chat_game:
            await chat_game.end_game(end_game)


async def start_game(game, chat_id, user):
    await game.start_game(user, end_game)
    if game.exclusive_user and await inc_user_fine(game):  # Проверка на штраф
        args = game.exclusive_user, game.exclusive_user_name
        log_game("Получил штраф", game, args)
        await bot.send_message(
            chat_id, **ui.get_fault_message(*args), **game.msg_kwargs
        )


@bot.message_handler(commands=["stats_global"], func=is_group_command)
async def stats_global(message: Message):
    """Общая статистика игры"""
    result = await get_global_stats()
    return await bot.send_message(
        message.chat.id, reply_to_message_id=message.message_id, **result
    )


@bot.message_handler(commands=["stats"], func=is_group_command)
async def stats(message: Message):
    """Статистика игры по чату"""
    result = await get_chat_stats(message.chat.id)
    kwargs = {}
    if message.is_topic_message:
        kwargs.update(message_thread_id=message.message_thread_id)
    return await bot.send_message(
        message.chat.id, reply_to_message_id=message.message_id, **result
    )


async def end_game(game):
    """Отправляем сообщение об окончании игры"""
    await bot.send_message(
        game.chat_id, **ui.get_end_game_message(game.current_word), **game.msg_kwargs
    )


@bot.message_handler(content_types=["text"], func=is_group_message)
async def chat_messages(message: Message):
    """Обработчик сообщений в чатах"""
    if message.from_user.id in TESTERS_IDS:
        print(":" * 55)
        print(f"{message.is_topic_message=}")
        print(f"{message.message_thread_id=}")
    chat_id = message.chat.id
    log = f"{chat_id} `{message.chat.title}` {message.from_user.full_name} :: {message.text}"
    print(log)
    chat_game = await Game.get_game(message)

    # Если игра не активна либо пишет ведущий, то выходим
    if not chat_game or message.from_user.id == chat_game.current_leader:
        return
    result = await check_user_answer(message, chat_game)  # Проверяем ответ из чата
    if result == -1:  # Повторный ответ
        try:
            await bot.delete_message(chat_id, message.message_id)
        except:
            pass
    elif result:  # Угадал слово
        log_game("Угадал слово", chat_game, message.from_user)
        await bot.send_message(
            chat_id,
            **ui.get_new_game_message(message.from_user, chat_game.current_word),
            **chat_game.msg_kwargs,
        )


@bot.edited_message_handler(content_types=["text"], func=is_group_message)
async def edited_chat_messages(message: Message):
    return await chat_messages(message)


@bot.callback_query_handler(func=lambda call: True)
async def callback_handler(call: CallbackQuery):
    chat_id = call.message.chat.id
    chat_game = await Game.get_game(call.message, start_game=True)

    if call.data == "want_to_lead" and not chat_game:
        if (
            chat_game.exclusive_timer
            and chat_game.exclusive_timer.time_remain > 0
            and call.from_user.id != chat_game.exclusive_user
        ):
            time_remain = chat_game.exclusive_timer.time_remain
            return await bot.answer_callback_query(
                call.id,
                f"Вы станете ведущим, если отгадавший не займет эту роль в течение {time_remain} сек.",
                show_alert=True,
            )
        await start_game(chat_game, chat_id, call.from_user)
        log_game("Новый ведущий", chat_game, call.from_user)
        await bot.answer_callback_query(
            call.id, text=f"Ваше слово: {chat_game.current_word}", show_alert=True
        )
        game_time = (chat_game.game_timer.interval + 29) // 60
        await bot.send_message(
            chat_id,
            **ui.get_lead_game_message(call.from_user, game_time),
            **chat_game.msg_kwargs,
        )
    elif call.data == "view_word" and call.from_user.id in TESTERS_IDS + (
        chat_game.current_leader,
    ):
        log_game("Посмотрел слово", chat_game, call.from_user)
        await bot.answer_callback_query(
            call.id, text=f"Ваше слово: {chat_game.current_word}", show_alert=True
        )
    elif call.data == "change_word" and call.from_user.id == chat_game.current_leader:
        chat_game.define_new_word()
        await chat_game.save_game()
        log_game("Сменил слово", chat_game, call.from_user)
        await bot.answer_callback_query(
            call.id, text=f"Ваше новое слово: {chat_game.current_word}", show_alert=True
        )
    elif call.from_user.id != chat_game.current_leader:
        await bot.answer_callback_query(call.id, text="Вы не ведущий", show_alert=True)
    else:
        await bot.answer_callback_query(call.id)


async def start_bot():
    await load_games(end_game_func=end_game)
    await bot.infinity_polling()


if __name__ == "__main__":
    asyncio.run(start_bot())
