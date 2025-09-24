from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from .bot_utils import is_manager


class ManagerMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # Проверяем, является ли пользователь менеджером
        if isinstance(event, (Message, CallbackQuery)):
            user_id = str(event.from_user.id)
            is_admin = await is_manager(user_id)

            if not is_admin:
                if isinstance(event, Message):
                    await event.answer("❌ У вас нет прав для выполнения этой команды")
                else:
                    await event.answer("❌ У вас нет прав")
                    await event.message.answer("❌ У вас нет прав для выполнения этой команды")
                return

        return await handler(event, data)