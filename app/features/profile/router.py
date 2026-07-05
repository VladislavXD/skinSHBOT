from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Message

from DB.repository import UserRepository
from app.shared.stetes import UserLanguage, UserProfileState
from app.shared.ui.main_menu import show_main_menu
from core.config import settings


router = Router(name="profile")


def _currency_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Рубль (RUB)", callback_data="currency:set:rub")],
            [InlineKeyboardButton(text="🇺🇸 Доллар (USD)", callback_data="currency:set:usd")],
            [InlineKeyboardButton(text="🇺🇿 Сум (UZS)", callback_data="currency:set:uzs")],
            [InlineKeyboardButton(text="🏠 В меню", callback_data="profile:back")],
        ]
    )


async def show_currency_selection_ui(
    bot,
    chat_id: int,
    message_id: int | None = None,
    text: str = "Выберите валюту отображения цен",
) -> None:
    if message_id:
        media = InputMediaPhoto(media=FSInputFile("./publick/images/main_menu.png"), caption=text)
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=media,
            reply_markup=_currency_keyboard(),
        )
    else:
        await bot.send_photo(
            chat_id=chat_id,
            photo=FSInputFile("./publick/images/main_menu.png"),
            caption=text,
            reply_markup=_currency_keyboard(),
        )


@router.callback_query(F.data == "menu:currency")
async def choose_currency_from_menu(call: CallbackQuery):
    await call.answer()
    await show_currency_selection_ui(call.bot, call.message.chat.id, call.message.message_id)


@router.callback_query(F.data.startswith("currency:set:"))
async def set_currency(call: CallbackQuery):
    currency = call.data.split(":")[-1]
    if currency not in {"rub", "usd", "uzs"}:
        await call.answer("Неизвестная валюта", show_alert=True)
        return

    await UserRepository.set_user_currency(call.message.chat.id, currency)
    await call.answer("Валюта обновлена")
    lang = await UserLanguage.get(call.message.chat.id)
    await show_main_menu(
        call.bot,
        call.message.chat.id,
        lang=lang,
        message_id=call.message.message_id,
        is_admin=call.message.chat.id == settings.admin_id,
    )


@router.callback_query(F.data == "menu:address")
async def set_address_start(call: CallbackQuery, state: FSMContext):
    user = await UserRepository.get_user(call.message.chat.id)
    current = user.default_address if user and user.default_address else "не указан"
    await state.set_state(UserProfileState.waiting_address)
    await state.update_data(origin_message_id=call.message.message_id)
    await call.answer()
    await call.message.edit_caption(
        caption=(
            "<b>Введите ваш адрес доставки</b>\n\n"
            f"Текущий адрес: {current}\n\n"
            "Пример:\n"
            "г. Ташкент, Мирзо-Улугбекский район, ул. Амира Темура 45, "
            "подъезд 2, этаж 5, кв. 27"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="profile:cancel_address")]]
        ),
    )


@router.message(UserProfileState.waiting_address)
async def set_address_value(message: Message, state: FSMContext):
    address = message.text.strip()
    if len(address) < 10:
        data = await state.get_data()
        await message.bot.edit_message_caption(
            chat_id=message.chat.id,
            message_id=data.get("origin_message_id"),
            caption="Адрес слишком короткий. Укажите полный адрес.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="profile:cancel_address")]]
            ),
        )
        return

    await UserRepository.set_user_address(message.chat.id, address)
    data = await state.get_data()
    await state.clear()
    lang = await UserLanguage.get(message.chat.id)
    await message.bot.edit_message_caption(
        chat_id=message.chat.id,
        message_id=data.get("origin_message_id"),
        caption="✅ Адрес сохранен",
        reply_markup=None,
    )
    await show_main_menu(
        message.bot,
        message.chat.id,
        lang=lang,
        message_id=data.get("origin_message_id"),
        is_admin=message.chat.id == settings.admin_id,
    )


@router.callback_query(F.data == "profile:cancel_address")
async def cancel_address_edit(call: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await UserLanguage.get(call.message.chat.id)
    await call.answer("Отменено")
    await show_main_menu(
        call.bot,
        call.message.chat.id,
        lang=lang,
        message_id=call.message.message_id,
        is_admin=call.message.chat.id == settings.admin_id,
    )


@router.callback_query(F.data == "profile:back")
async def profile_back_to_menu(call: CallbackQuery):
    lang = await UserLanguage.get(call.message.chat.id)
    await call.answer()
    await show_main_menu(
        call.bot,
        call.message.chat.id,
        lang=lang,
        message_id=call.message.message_id,
        is_admin=call.message.chat.id == settings.admin_id,
    )
