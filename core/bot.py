from aiogram import Bot, Dispatcher
from core.config import settings
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage


bot = Bot(
  token=settings.token,
  default=DefaultBotProperties(parse_mode=ParseMode.HTML) 
  )


storege = MemoryStorage()
dp = Dispatcher(storage=storege)