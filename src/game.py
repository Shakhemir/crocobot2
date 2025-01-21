import asyncio
import json
import random
import time
from telebot.types import Message, User
from src.config import settings


class Timer:
    def __new__(cls, *args, **kwargs):
        # При восстановлении таймера проверяем актуален ли он еще
        if end_time := kwargs.get("end_time"):
            if time.time() >= end_time:
                return None
        return super().__new__(cls)

    def __init__(self, interval: int | dict, callback, args=None, kwargs=None):
        current_time = time.time()
        if isinstance(
            interval, dict
        ):  # Если задано время окончания при восстановлении таймера
            self.interval = interval["interval"]
            end_time = interval["end_time"]
            self.start_time = end_time - self.interval
            self.timeout = end_time - current_time  # высчитываем остаток
            self.end_time = end_time
        else:  # Если таймер создается с нуля
            self.interval = interval
            self.start_time = current_time
            self.timeout = interval
            self.end_time = current_time + interval
        self._callback = callback
        self._args = args or ()
        self._kwargs = kwargs or {}
        self._task = asyncio.ensure_future(self._job())

    async def _job(self):
        await asyncio.sleep(self.timeout)
        await self._callback(*self._args, **self._kwargs)

    def cancel(self):
        self._task.cancel()

    @property
    def time_left(self):
        """Сколько секунд прошло"""
        return int(time.time() - self.start_time)

    @property
    def time_remain(self):
        """Сколько секунд осталось"""
        return self.interval - self.time_left

    def __repr__(self):
        return f"interval={self.interval}, left={self.time_left}, remain={self.time_remain}"

    def __str__(self):
        return self.__repr__()


class Game:
    def __init__(
        self, message: Message = None, word_gen_func=None, save_game_func=None, **kwargs
    ):
        self._word_gen_func = word_gen_func  # Функция генерации случайного слова
        self._save_game_func = save_game_func  # Функция сохранения состояния игры

        # Информация о чате, где проходит игра
        self.chat_id = self.chat_title = None
        if message:
            self.chat_id = message.chat.id
            self.chat_title = message.chat.title

        self.active = False  # Активна ли игра
        self.used_words = set()  # Множество угаданных слов
        self.game_timer: Timer | None = None  # Таймер игры
        self.current_leader: int | None = None  # Ведущий
        self.leader_name: str | None = None  # Имя ведущего
        self.current_word: str | None = None  # Загаданное слово
        self.next_words = []  # Очередь следующих слов, подкинутых админом
        self.answers_set = set()  # Множество использованных ответов
        self.exclusive_user: int | None = (
            None  # Угадавший игрок, имеющий исключительное право стать ведущим
        )
        self.exclusive_user_name: int | None = None  # Имя угадавшего
        self.exclusive_timer: Timer | None = None  # Таймер
        self.players = set()  # Сколько игроков угадывали

    async def save_game(self):
        """Сохранение состояния игры"""
        if self._save_game_func:
            await self._save_game_func(self)

    async def start_game(self, user, end_game_func):
        """Запуск игры"""
        self.active = True
        if self.exclusive_timer:
            self.exclusive_timer.cancel()

        # Назначаем нового ведущего
        self.current_leader = user.id
        self.leader_name = user.full_name
        self.define_new_word()

        # Запускаем таймер игры
        if self.game_timer:
            self.game_timer.cancel()
        self.game_timer = Timer(settings.GAME_TIME, self.end_game, (end_game_func,))

        # Сохраняем игру
        await self.save_game()

    def define_new_word(self):
        self.current_word = self._word_gen_func(self)
        self.answers_set.clear()

    async def add_current_word_to_used(self, user: User):
        """Слово угадали"""
        self.active = False
        self.game_timer.cancel()
        self.exclusive_timer = Timer(settings.EXCLUSIVE_TIME, self.end_exclusive)
        self.exclusive_user = user.id
        self.exclusive_user_name = user.full_name
        self.used_words.add(self.current_word)
        if self.players is None:  # TODO временная проверка
            self.players = set()
        player = f"{user.id} {user.full_name}"
        if user.username:
            player += f" @{user.username}"
        self.players.add(player)
        self.answers_set.clear()
        await self.save_game()

    async def end_exclusive(self):
        self.exclusive_timer = None
        await self.save_game()

    async def end_game(self, end_game_func):
        """Игра закончилась по истечении времени, слово не угадали"""
        self.active = False
        self.game_timer = None
        self.exclusive_user = None
        self.answers_set.clear()
        await end_game_func(self)
        await self.save_game()

    def save_state(self):
        """Сохраняет состояние игры в словарь."""
        # Составляем словарь только из сериализуемых объектов
        state = {
            key: value for key, value in self.__dict__.items() if not callable(value)
        }
        if self.game_timer is not None:
            state["game_timer"] = {
                "interval": self.game_timer.interval,
                "end_time": self.game_timer.end_time,
            }
        if self.exclusive_timer is not None:
            state["exclusive_timer"] = {
                "interval": self.exclusive_timer.interval,
                "end_time": self.exclusive_timer.end_time,
            }
        return state

    @classmethod
    async def load_state(cls, state, **kwargs):
        """Восстанавливает экземпляр игры из словаря состояния."""
        obj = cls(**kwargs)
        for key, value in state.items():
            if key in ("game_timer", "exclusive_timer"):
                continue
            if value:
                setattr(obj, key, value)

        # Восстановление таймеров
        end_game_func = kwargs.get("end_game_func")
        if end_game_func and (timer_state := state.get("game_timer")):
            obj.game_timer = Timer(timer_state, obj.end_game, (end_game_func,))
            if obj.active and obj.game_timer is None:
                await end_game_func(obj)

        if exclusive_state := state.get("exclusive_timer"):
            obj.exclusive_timer = Timer(exclusive_state, obj.end_exclusive)

        return obj

    def __bool__(self):
        return self.active

    def __str__(self):
        def dumps_default(obj):
            if isinstance(obj, set):
                res = list(obj)
                if (l := len(res)) > 6:
                    res = random.sample(res, 5)
                    res.append(f"… {l} items")
                return res
            if isinstance(obj, Timer):
                return str(obj)

        state = {
            key: value for key, value in self.__dict__.items() if not callable(value)
        }
        try:
            return json.dumps(
                state, indent=4, ensure_ascii=False, default=dumps_default
            )
        except:
            return str(state)

    def __repr__(self):
        return f"Game<'{self.chat_title}', {self.chat_id}>"
