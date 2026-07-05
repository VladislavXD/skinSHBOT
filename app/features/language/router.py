# features/language/router.py
from aiogram import Router, F
from aiogram.types import CallbackQuery

from DB.repository import UserRepository
from app.features.profile.router import show_currency_selection_ui
from app.shared.stetes import UserLanguage
from app.shared.ui.main_menu import show_main_menu
from app.shared.ui.language import show_language_selection
from core.config import settings
router = Router(name="language")


@router.callback_query(F.data.startswith('lang_'))
async def select_language(call: CallbackQuery):
    lang = call.data.split('_')[1]
    await UserLanguage.set(call.message.chat.id, lang)

    await call.answer({'en': "Language updated!", 'ru': "Язык изменен!",
                        'uz': "Til o'zgartirildi!"}.get(lang))

    actual_user = await UserRepository.get_user(call.message.chat.id)
    if actual_user and not actual_user.currency_selected:
        await show_currency_selection_ui(
            call.bot,
            call.message.chat.id,
            call.message.message_id,
            text="Выберите валюту (по умолчанию RUB)",
        )
        return

    await show_main_menu(
        call.bot,
        call.message.chat.id,
        lang=lang,
        message_id=call.message.message_id,
        is_admin=call.message.chat.id == settings.admin_id,
    )
    
@router.callback_query(F.data == 'change_language')
async def change_language(call: CallbackQuery):
    await show_language_selection(call.bot, call.message.chat.id, message_id=call.message.message_id)
    