from telebot import util
from telebot.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def get_welcome_message(bot_title):
    text = (
        """
    🙋 <b>Добро пожаловать в бот "%s"!</b>

    Это бот для игры в <b>Крокодила</b>, предназначенный для использования в <b>групповых чатах</b>.

    🎮 <b>Как играть?</b>
    1. Добавьте бота в группу.
    2. Используйте команду <code>/start</code>, чтобы начать игру.

    🛠️ Бот был создан недавно айтишным энтузиастом и продолжает активно развиваться. Ожидайте новых функций и обновлений! 🚀

    🕹 Общий чат крокодила где может поиграть любой желающий: @game_crocochat

    📩 По всем вопросам обращайтесь: @kudanoff
    """
        % bot_title
    )
    return dict(
        text=text,
        parse_mode="html",
    )


leader_markup = InlineKeyboardMarkup()
view_word_btn = InlineKeyboardButton("🔎 Посмотреть слово", callback_data="view_word")
change_word_btn = InlineKeyboardButton("🔄 Сменить слово", callback_data="change_word")
leader_markup.add(view_word_btn, change_word_btn)
# leader_markup.add(change_word_btn)


def get_start_game_message(user_name):
    text = f"Игра начинается! <b>{user_name}</b> объясняет слово ⚡️\n\nВедущий, выберите действие:"
    return dict(
        text=text,
        parse_mode="html",
        reply_markup=leader_markup,
    )


def get_game_already_started_message():
    text = "Игра уже запущена. Дождитесь окончания текущей игры."
    return dict(text=text)


def get_end_game_message():
    text = "Игра закончена. Нажмите /start, чтобы начать заново."
    return dict(
        text=text,
    )
