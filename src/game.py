import asyncio
import json
import time
from telebot.types import Message
from src.config import settings
import src.user_interface as ui


class Timer:
    def __init__(self, timeout, callback, args=None, kwargs=None):
        self.interval = timeout
        self._callback = callback
        self._args = args or ()
        self._kwargs = kwargs or {}
        self.start_time = int(time.time())  # Засекаем время начала
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        await asyncio.sleep(self.interval)
        await self._callback(*self._args, **self._kwargs)

    def cancel(self):
        self._task.cancel()

    @property
    def time_left(self):
        """Сколько секунд прошло"""
        return int(time.time()) - self.start_time

    @property
    def time_remain(self):
        """Сколько секунд осталось"""
        return self.interval - self.time_left

    def __repr__(self):
        return f"interval={self.interval}, left={self.time_left}, remain={self.time_remain}"

    def __str__(self):
        return self.__repr__()


class Game:
    def __init__(self, message: Message = None):
        self.bot = None
        self.func_word_gen = None  # Функция генерации случайного слова
        # Информация о чате, где проходит игра
        self.chat_id = message.chat.id
        self.chat_title = message.chat.title

        self.active: bool | None = None  # Активна ли игра
        self.used_words = set()  # Множество угаданных слов
        self.game_timer: Timer | None = None  # Таймер игры
        self.current_leader: int | None = None  # Ведущий
        self.leader_name: str | None = None  # Имя ведущего
        self.current_word: str | None = None  # Загаданное слово
        self.answers_set: set | None = None  # Множество использованных ответов
        self.exclusive_user: int | None = (
            None  # Угадавший игрок, имеющий исключительное право стать ведущим
        )
        self.exclusive_timer: Timer | None = (
            None  # Таймер для исключительного права стать ведущим
        )
        self.players: int | None = None  # Сколько игроков угадывали

    async def start_game(self, bot, message, word_gen_func):
        """Запуск игры"""
        self.bot = bot
        self.func_word_gen = word_gen_func
        self.active = True
        # Назначаем нового ведущего
        self.current_leader = message.from_user.id
        self.leader_name = message.from_user.full_name
        self.define_new_word()
        # Запускаем таймер игры
        self.game_timer = Timer(settings.GAME_TIME, self.end_game)

    async def end_game(self):
        self.active = False
        await self.bot.send_message(self.chat_id, **ui.get_end_game_message())

    def define_new_word(self):
        self.current_word = self.func_word_gen(self)

    def __bool__(self):
        return self.active

    def __str__(self):
        try:
            return json.dumps(self.__dict__, indent=4, ensure_ascii=False)
        except:
            return str(self.__dict__)

    def __repr__(self):
        return f"Game<'{self.chat_title}', {self.chat_id}>"
