from telebot import util
from typing import Any
from telebot.types import Message, CallbackQuery
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_handler_backends import ContinueHandling
from telebot.asyncio_handler_backends import State, StatesGroup


class GameStates(StatesGroup):
    start = State()
    end = State()


class MyTeleBot(AsyncTeleBot):
    """
    Дополненная версия асинхронного телебота
    """

    States = GameStates

    def __init__(self, token, *args, tester_ids=None, **kwargs):
        super().__init__(token, *args, **kwargs)
        self.tester_ids = tester_ids
        self.add_message_handler(
            self._build_handler_dict(
                self.admin_mode,
                commands=["admin"],
                func=lambda message: message.chat.id in self.tester_ids,
            )
        )
        self.add_callback_query_handler(
            self._build_handler_dict(
                self.admin_inline_buttons,
                func=lambda call: call.message.chat.id in self.tester_ids,
            )
        )

    async def message_to_tester(self, msg: str, place: str = None):
        """
        Отправка сообщений разработчику, для тестирования
        """

        text = "<b>Ахтунг</b>"
        if place is not None:
            text += f"<b> в </b><code>{place}</code>"
        text += f":\n\n<i>{msg}</i>"
        await self.send_message(self.tester_ids[0], text, parse_mode="html")

    async def get_stored_data(self, message: Message | int, *args) -> list | Any | None:
        """Извлекаем контекстные данные"""
        chat_id = message if isinstance(message, int) else message.chat.id
        result = []
        async with self.retrieve_data(chat_id) as data:
            if data is None:
                return
            for arg in args:
                result.append(data.get(arg))
        if len(result) == 1:
            return result[0]
        return result

    async def set_stored_data(self, message: Message | int, **kwargs):
        """Заносим контекстные данные"""
        chat_id = message if isinstance(message, int) else message.chat.id
        async with self.retrieve_data(chat_id) as data:
            if data is None:
                data = {}
            data.update(**kwargs)

    async def init_common_sate(self):
        await self.set_state(1, self.States.start)

    async def get_common_data(self, *args) -> list | Any | None:
        """Извлекаем контекстные данные, не привязанные к чату"""
        return await self.get_stored_data(1, *args)

    async def set_common_data(self, **kwargs):
        """Заносим контекстные данные, не привязанные к чату"""
        await self.set_stored_data(1, **kwargs)

    async def admin_mode(self, message: Message):
        """Меню админа"""
        markup = util.quick_markup(
            {
                "Скачать БД": {"callback_data": "download_db"},
            }
        )
        await self.send_message(message.chat.id, "Меню:", reply_markup=markup)

    async def admin_inline_buttons(self, call: CallbackQuery):
        """Меню админа"""
        if call.data == "download_db":  # Скачиваем БД
            with open("data.db", "rb") as f:
                await self.send_document(self.tester_ids, f)
        await self.answer_callback_query(call.id)
        return ContinueHandling()
