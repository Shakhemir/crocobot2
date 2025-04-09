from random import randint
from telebot import util
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from app import gpt
from src.settings import settings
from src.utils import log_error


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
    text = f"🕹 <b>Игра начинается!</b>\n\n<b>{user_name}</b> объясняет слово ⚡️\nВремя раунда <b>{minutes}</b> {m}\n\nВедущий, объясняй слово игрокам"
    return dict(
        text=text,
        parse_mode="html",
        reply_markup=leader_markup,
    )


def get_lead_game_message(user, minutes):
    user_name = util.user_link(user)
    m = get_correct_word_form(minutes)
    word_of_gpt = gpt_injection()
    text = f"<b>{user_name}</b> объясняет слово ⚡️\nВремя раунда <b>{minutes}</b> {m}\n{word_of_gpt}"
    return dict(
        text=text,
        parse_mode="html",
        reply_markup=leader_markup,
    )


def get_game_already_started_message():
    text = "Игра уже запущена. Предыдущее слово еще не отгадано."
    return dict(text=text)


def get_end_game_message(word):
    word_of_gpt = gpt_injection(
        "Напиши мотивационный текст в одном предложении для участия в игре, где нужно объяснить загаданное слово другими словами. Тон должен быть в меру строгим, с тонкой ноткой завуалированного и красивого юмора и с не более 210 символов. В тексте не упоминай, что это виртуальная игра «Крокодил». Упомяни правило: . Ответ должен содержать только готовое предложение."
    )
    text = (
        f"<b>Игра завершена :(</b>\nЗагаданное слово было: <b>{word}</b>.\n{word_of_gpt}\n"
        f"Нажмите /start, чтобы возобновить игру."
    )
    return dict(text=text, reply_markup=make_lead_markup, parse_mode="HTML")


def get_new_game_message(user, current_word):
    user_link = util.user_link(user)
    word_of_gpt = gpt_injection(
        "Напиши мотивационный текст в одном предложении для участия в игре, где нужно объяснить загаданное слово другими словами. Тон должен быть в меру строгим, с тонкой ноткой завуалированного юмора и с не более 210 символов. В тексте не упоминай, что это виртуальная игра «Крокодил». Добавь пожелание следующему ведущему и укажи не использовать однокоренные слова. Упомяни правило: без использования однокоренных слов. Ответ должен содержать только готовое предложение."
    )
    text = f"⚡️ {user_link} отгадал(-а) слово <b>{current_word}</b>!\n{word_of_gpt}\nКто хочет следующим ведущим?"
    return dict(text=text, reply_markup=make_lead_markup, parse_mode="HTML")


def get_fault_message(user_id, user_name):
    user_name = util.escape(user_name)
    user_link = f"<a href='tg://user?id={user_id}'>{user_name}</a>"
    text = f"Игрок {user_link} был лишён одного очка за повторный отказ стать ведущим в игре. Ну, бывает:))"
    return dict(text=text, parse_mode="HTML")


def gpt_injection(prompt: str = None) -> str:
    """
    Вставка текстов мотивации от модели ChatGPT.
    Чтобы заработал, надо внести промпт в файл gpt-prompt.txt.
    Функция считывает содержимое этого файла каждый раз,
    когда к ней обращаются. Поэтому не нужно перезагружать бота,
    если изменился промпт.
    """
    if prompt is None:
        try:
            with open(settings.PROMPT_FILE, encoding="utf-8") as f:
                prompt = f.read().strip()
        except FileNotFoundError:
            prompt = ""

    if prompt and randint(1, 5) == 1:
        try:
            gpt_joke = "\n" + gpt.generate_answer(prompt) + "\n"
        except Exception as e:
            log_error(str(e))
            return ""
        return f"<i>{gpt_joke}</i>"
    else:
        return ""
