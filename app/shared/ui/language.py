# shared/ui/language.py
from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton


def language_selection_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz")],
    ])


async def show_language_selection(bot: Bot, chat_id: int, message_id: int | None = None):
    caption = "Select your language / Выберите язык / Tilni tanlang:"
    kb = language_selection_keyboard()

    if message_id:
        from aiogram.types import InputMediaPhoto
        media = InputMediaPhoto(media=FSInputFile("./publick/images/main_menu.png"), caption=caption)
        await bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media, reply_markup=kb)
    else:
        await bot.send_photo(chat_id=chat_id, photo=FSInputFile("./publick/images/main_menu.png"),
                              caption=caption, reply_markup=kb)