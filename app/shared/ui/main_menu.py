# shared/ui/main_menu.py
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton

from app.features.language.get_text import get_text


def main_menu_keyboard(lang: str, is_admin: bool = False) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text=get_text("btn_catalog", lang), callback_data="menu:catalog")],
        [InlineKeyboardButton(text=get_text("btn_cart", lang), callback_data="menu:cart")],
        [InlineKeyboardButton(text=get_text("btn_currency", lang), callback_data="menu:currency")],
        [InlineKeyboardButton(text=get_text("btn_address", lang), callback_data="menu:address")],
        [InlineKeyboardButton(text=get_text("btn_lang", lang), callback_data="change_language")],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton(text=get_text("btn_admin", lang), callback_data="admin:panel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def show_main_menu(
    bot: Bot,
    chat_id: int,
    lang: str = 'ru',
    message_id: int | None = None,
    is_admin: bool = False,
):
    """
    Единая точка рендера главного меню.
    Если message_id передан — редактируем существующее сообщение (плавный переход).
    Если нет — отправляем новое (первый заход, /start).
    """
    caption = get_text("main_menu", lang)
    kb = main_menu_keyboard(lang, is_admin=is_admin)

    if message_id:
        media = InputMediaPhoto(media=FSInputFile("./publick/images/main_menu.png"),
                                 caption=caption, parse_mode="HTML")
        try:
            await bot.edit_message_media(chat_id=chat_id, message_id=message_id,
                                          media=media, reply_markup=kb)
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc):
                raise
    else:
        await bot.send_photo(chat_id=chat_id, photo=FSInputFile("./publick/images/main_menu.png"),
                              caption=caption, parse_mode="HTML", reply_markup=kb)