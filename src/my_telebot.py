from telebot import util, types, asyncio_helper
from typing import Any, Union, Optional, List
from telebot.types import Message, CallbackQuery
from telebot.async_telebot import AsyncTeleBot, REPLY_MARKUP_TYPES
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

    async def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: Optional[str] = None,
        entities: Optional[List[types.MessageEntity]] = None,
        disable_web_page_preview: Optional[bool] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: Optional[bool] = None,
        reply_markup: Optional[REPLY_MARKUP_TYPES] = None,
        timeout: Optional[int] = None,
        message_thread_id: Optional[int] = None,
        reply_parameters: Optional[types.ReplyParameters] = None,
        link_preview_options: Optional[types.LinkPreviewOptions] = None,
        business_connection_id: Optional[str] = None,
        message_effect_id: Optional[str] = None,
        allow_paid_broadcast: Optional[bool] = None,
    ) -> types.Message:
        try:
            return await super().send_message(
                chat_id,
                text,
                parse_mode,
                entities,
                disable_web_page_preview,
                disable_notification,
                protect_content,
                reply_to_message_id,
                allow_sending_without_reply,
                reply_markup,
                timeout,
                message_thread_id,
                reply_parameters,
                link_preview_options,
                business_connection_id,
                message_effect_id,
                allow_paid_broadcast,
            )
        except asyncio_helper.ApiTelegramException as e:
            print(e)

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
