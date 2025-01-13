from telebot import util
from telebot.types import KeyboardButton, ReplyKeyboardMarkup


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


def get_start_game_message(user_name):
    text = f"Игра начинается! <b>{user_name}</b> объясняет слово ⚡️\n\nВедущий, выберите действие:"
    return dict(
        text=text,
        parse_mode="html",
    )


def get_end_game_message():
    text = "Игра закончена. Нажмите /start, чтобы начать заново."
    return dict(
        text=text,
    )
