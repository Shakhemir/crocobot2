import asyncio
import json
import pickle
import random
import time
import aiofiles
from telebot.types import Message, User
from app.words_generator import get_random_word
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
    games: dict[str, "Game"] = {}
    _word_gen_func = get_random_word

    # Множество айди чатов обсуждений, привязанных к постам каналов
    chats_posts: dict[int, set] = {}

    @classmethod
    def get_game_chat_id(cls, message: Message | str) -> str:
        """Формирует chat_id для чата игры с учетом топиков и постов канала"""
        if isinstance(message, str):  # возвращает как есть
            return message
        if message.is_topic_message:  # чат топика
            return f"{message.chat.id}-{message.message_thread_id}"
        if message.message_thread_id is not None:
            if (
                message.message_thread_id in cls.chats_posts.get(message.chat.id, set())
                or message.reply_to_message.from_user.id == 777000
            ):
                # чат поста канала
                return f"{message.chat.id}-post-{message.message_thread_id}"
        return str(message.chat.id)  # обычный чат

    @classmethod
    async def get_game(cls, message: Message | str, start_game: bool = None):
        chat_id = cls.get_game_chat_id(message)
        game = cls.games.get(chat_id)
        if (
            game is None and start_game
        ):  # Если игра не найдена, а надо стартовать, то создаем
            game = cls(chat_id, message)
            cls.games[chat_id] = game
            await cls.save_game(game)
        elif start_game:
            game.define_chat_name(message)
            await game.save_game()
        return game

    def __init__(
        self,
        game_chat_id: str,
        message: Message = None,
        **kwargs,  # don't remove
    ):
        self.game_chat_id = game_chat_id  # этот айди используется как ключ в словаре games и в именовании файла .pkl
        self.check_if_channel_post()

        # Информация о чате, где проходит игра
        self.chat_id = self.chat_title = self.topic_id = self.topic_name = (
            self.chat_username
        ) = None
        self.msg_kwargs = {}  # kwargs для отправки сообщений в бот
        if message:
            self.chat_id = message.chat.id
            self.define_chat_name(message)
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

    def define_chat_name(self, message: Message):
        """Определяет имя чата, топика, разные айди для определения постов и топиков"""
        self.chat_title = message.chat.title
        self.chat_username = (
            "@" + message.chat.username if message.chat.username else None
        )
        if message.is_topic_message:
            self.topic_id = message.message_thread_id
            if message.reply_to_message.forum_topic_created:
                self.topic_name = message.reply_to_message.forum_topic_created.name
        else:
            self.topic_id = self.topic_name = None
        self.define_msg_kwargs(message)

    def check_if_channel_post(self):
        if "post" in self.game_chat_id:
            # Добавляем айди поста в множество чата
            chat_id, post_id = map(int, self.game_chat_id.split("-post-"))
            chat_posts = self.__class__.chats_posts.get(chat_id, set())
            chat_posts.add(post_id)
            self.__class__.chats_posts[chat_id] = chat_posts

    def define_msg_kwargs(self, message: Message):
        if message.is_topic_message:
            self.msg_kwargs.update(message_thread_id=message.message_thread_id)
        elif (
            message.message_thread_id is not None
            and message.message_thread_id
            in self.__class__.chats_posts.get(message.chat.id, set())
        ):
            self.msg_kwargs.update(reply_to_message_id=message.message_thread_id)
        else:
            self.msg_kwargs = {}

    async def save_game(self):
        """Сохранение состояния игры"""
        async with aiofiles.open(
            f"{settings.STATE_SAVE_DIR}{self.game_chat_id}.pkl", "wb"
        ) as f:
            await f.write(pickle.dumps(self.save_state()))

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
        self.current_word = self._word_gen_func()
        self.answers_set.clear()

    async def add_current_word_to_used(self, user: User):
        """Слово угадали"""
        self.active = False
        self.game_timer.cancel()
        self.exclusive_timer = Timer(settings.EXCLUSIVE_TIME, self.end_exclusive)
        self.exclusive_user = user.id
        self.exclusive_user_name = user.full_name
        self.used_words.add(self.current_word)
        if self.players is None:
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
        self.game_timer = None
        self.exclusive_user = None
        self.answers_set.clear()
        if self.active:
            self.active = False
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
