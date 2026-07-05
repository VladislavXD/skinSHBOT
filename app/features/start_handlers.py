# features/start/router.py
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.features.profile.router import show_currency_selection_ui
from app.shared.stetes import UserLanguage
from app.shared.ui.main_menu import show_main_menu
from app.shared.ui.language import show_language_selection
from DB.repository import UserRepository
from core.config import settings

router = Router(name="start_handlers")


@router.message(CommandStart())
async def start_handler(message: Message):
    user = await UserRepository.get_user(message.chat.id)

    if not user:
        # новый пользователь → сначала выбор языка, язык ещё не определён
        await UserRepository.create_user(message.chat.id, name=message.from_user.full_name or "")
        await show_language_selection(message.bot, message.chat.id)
        return

    # пользователь уже существует → сразу главное меню на его языке
    lang = await UserLanguage.get(message.chat.id)
    if user and not user.currency_selected:
        await show_currency_selection_ui(
            message.bot,
            message.chat.id,
            text="Выберите валюту (по умолчанию RUB).",
        )
        return

    await show_main_menu(
        message.bot,
        message.chat.id,
        lang=lang,
        is_admin=message.chat.id == settings.admin_id,
    )