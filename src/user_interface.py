from telebot import util
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


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


# Кнопка для выбора ведущего
make_lead_markup = InlineKeyboardMarkup()
want_to_lead_btn = InlineKeyboardButton(
    "Стать ведущим 🐳", callback_data="want_to_lead"
)
make_lead_markup.add(want_to_lead_btn)

# Кнопки для ведущего
leader_markup = InlineKeyboardMarkup()
change_word_btn = InlineKeyboardButton("🔄 Сменить", callback_data="change_word")
view_word_btn = InlineKeyboardButton("🔎 Посмотреть", callback_data="view_word")
leader_markup.add(change_word_btn, view_word_btn)


def get_correct_word_form(count):
    if count % 10 == 1 and count % 100 != 11:
        return "минута"
    elif 2 <= count % 10 <= 4 and not (12 <= count % 100 <= 14):
        return "минуты"
    else:
        return "минут"


def get_start_game_message(user, minutes):
    user_name = util.user_link(user)
    m = get_correct_word_form(minutes)
    text = f"Игра начинается!\n\n<b>{user_name}</b> объясняет слово ⚡️\nВремя игры <b>{minutes}</b> {m}\n\nВедущий, объясняй слово"
    return dict(
        text=text,
        parse_mode="html",
        reply_markup=leader_markup,
    )


def get_lead_game_message(user, minutes):
    user_name = util.user_link(user)
    m = get_correct_word_form(minutes)
    text = f"<b>{user_name}</b> объясняет слово ⚡️\nВремя игры <b>{minutes}</b> {m}"
    return dict(
        text=text,
        parse_mode="html",
        reply_markup=leader_markup,
    )


def get_game_already_started_message():
    text = "Игра уже запущена. Предыдущее слово еще не отгадано."
    return dict(text=text)


def get_end_game_message(word):
    text = f"Игра завершена :(\n\nЗагаданное слово было: <b>{word}</b>.\n\nНажмите /start, чтобы начать игру."
    return dict(text=text, reply_markup=make_lead_markup, parse_mode="HTML")


def get_new_game_message(user, current_word):
    user_link = util.user_link(user)
    text = f"😜 {user_link} отгадал(-а) слово <b>{current_word}</b>!\n\nКто хочет быть ведущим?"
    return dict(text=text, reply_markup=make_lead_markup, parse_mode="HTML")


def get_fault_message(user_id, user_name):
    user_name = util.escape(user_name)
    user_link = f"<a href='tg://user?id={user_id}'>{user_name}</a>"
    text = f"Игрок {user_link} был лишён одного очка за повторный отказ стать ведущим в игре. Бывает:))"
    return dict(text=text, parse_mode="HTML")
