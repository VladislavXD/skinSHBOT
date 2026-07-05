# features/language/texts.py

translations = {
    "main_menu": {
        "en": "👋 Welcome to <b>STREET LAB</b>\n\nWhere should we start? 👇",
        "ru": "👋 Добро пожаловать в <b>STREET LAB</b>\n\nВыберите, с чего начать 👇",
        "uz": "👋 <b>STREET LAB</b>ga xush kelibsiz\n\nNimadan boshlaymiz? 👇",
    },
    "btn_catalog": {
        "en": "🛍 Catalog",
        "ru": "🛍 Каталог",
        "uz": "🛍 Katalog",
    },
    "btn_cart": {
        "en": "🛒 Cart",
        "ru": "🛒 Корзина",
        "uz": "🛒 Savat",
    },
    "btn_lang": {
        "en": "🌐 Language",
        "ru": "🌐 Язык",
        "uz": "🌐 Til",
    },
    "btn_admin": {
        "en": "⚙️ Admin",
        "ru": "⚙️ Админ",
        "uz": "⚙️ Admin",
    },
    "btn_currency": {
        "en": "💱 Currency",
        "ru": "💱 Валюта",
        "uz": "💱 Valyuta",
    },
    "btn_address": {
        "en": "📍 Address",
        "ru": "📍 Адрес",
        "uz": "📍 Manzil",
    },
}


def get_text(key: str, language: str) -> str:
    return translations.get(key, {}).get(language, key)