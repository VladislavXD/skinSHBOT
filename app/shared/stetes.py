# shared/states.py
from aiogram.fsm.state import State, StatesGroup
from DB.repository import UserRepository

class Form(StatesGroup):
    waiting_for_ip = State()
    waiting_for_message = State()
    wait_for_tts = State()
    search_phone = State()
    search_user = State()
    search_photo = State()
    waiting_for_download_url = State()


class AdminCategoryCreate(StatesGroup):
    waiting_name = State()
    waiting_name_en = State()
    waiting_name_uz = State()
    waiting_description = State()
    waiting_description_en = State()
    waiting_description_uz = State()
    waiting_photo = State()
    waiting_emoji = State()
    waiting_sort_order = State()


class AdminProductCreate(StatesGroup):
    waiting_category = State()
    waiting_name = State()
    waiting_name_en = State()
    waiting_name_uz = State()
    waiting_description = State()
    waiting_description_en = State()
    waiting_description_uz = State()
    waiting_price = State()
    waiting_old_price = State()
    waiting_stock = State()
    waiting_is_active = State()
    waiting_photos = State()
    waiting_confirm = State()


class CheckoutState(StatesGroup):
    waiting_quantity = State()
    waiting_address = State()
    waiting_payment_method = State()


class UserProfileState(StatesGroup):
    waiting_address = State()


class UserLanguage:
    _cache: dict[int, str] = {}

    @classmethod
    async def get(cls, user_id: int, lang: str = "ru") -> None:

        # если есть в кеше - отдаем
        if(user_id in cls._cache):
            return cls._cache[user_id] 
        
        # если нет в кеше - идем в бд и сохраняем в кеш
        user = await UserRepository.get_user(user_id)
        lang = user.language if user else lang
        
        
        cls._cache[user_id] = lang
        return lang

    @classmethod
    async def set(cls, user_id: int, lang: str = "en") -> str:
        cls._cache[user_id] = lang
        await UserRepository.set_user_language(user_id, lang)


      
  
  
