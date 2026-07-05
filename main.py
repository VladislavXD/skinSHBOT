from core.bot import dp, bot
from DB.repository import init_db
import asyncio
import logging
from app.features.start_handlers import router as start_router
from app.features.language.router import router as language_router
from app.features.catalog.router import router as catalog_router
from app.features.admin.router import router as admin_router
from app.features.cart.router import router as cart_router
from app.features.profile.router import router as profile_router

def setup_routers():
	dp.include_router(start_router)
	dp.include_router(language_router)
	dp.include_router(catalog_router)
	dp.include_router(admin_router)
	dp.include_router(cart_router)
	dp.include_router(profile_router)


def setup_middlewares():
  pass


async def main(): 
	setup_routers()
	setup_middlewares()
	await init_db()	
	await bot.delete_webhook(drop_pending_updates=True)
	await dp.start_polling(bot)
	
  

if __name__ == "__main__": 
	try: 
		logging.basicConfig(
			level=logging.INFO,
			format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
		)
		asyncio.run(main())
	except (KeyboardInterrupt, SystemExit):
		logging.error("Bot stopped!")