from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto

from decimal import Decimal

from DB.repository import CategoryRepository, ProductRepository, UserRepository
from app.shared.currency import format_money_from_rub
from app.shared.stetes import CheckoutState, UserLanguage


router = Router(name="catalog")
MAIN_MENU_IMAGE = "./publick/images/main_menu.png"
FALLBACK_CATEGORY_IMAGE = "./publick/images/main_menu.png"


def _catalog_keyboard(category_id: int, product_id: int, photo_index: int, photos_count: int) -> InlineKeyboardMarkup:
	photo_prev = (photo_index - 1) % photos_count
	photo_next = (photo_index + 1) % photos_count
	return InlineKeyboardMarkup(
		inline_keyboard=[
			[
				InlineKeyboardButton(text="🛒 В корзину", callback_data=f"catalog:add_to_cart:{product_id}"),
				InlineKeyboardButton(text="⚡ Купить", callback_data=f"catalog:buy_now:{product_id}"),
			],
			[
				InlineKeyboardButton(text="⬅️ Товар", callback_data=f"catalog:product:{category_id}:{product_id}:prev"),
				InlineKeyboardButton(text="Товар ➡️", callback_data=f"catalog:product:{category_id}:{product_id}:next"),
			],
			[
				InlineKeyboardButton(text="◀️ Фото", callback_data=f"catalog:photo:{category_id}:{product_id}:{photo_prev}"),
				InlineKeyboardButton(text="Фото ▶️", callback_data=f"catalog:photo:{category_id}:{product_id}:{photo_next}"),
			],
			[
				InlineKeyboardButton(text="◀️ К категориям", callback_data=f"catalog:category:{category_id}"),
				InlineKeyboardButton(text="🏠 В меню", callback_data="catalog:back"),
			],
		]
	)


def _category_keyboard(category_id: int) -> InlineKeyboardMarkup:
	return InlineKeyboardMarkup(
		inline_keyboard=[
			[
				InlineKeyboardButton(text="⬅️ Категория", callback_data=f"catalog:category_switch:{category_id}:prev"),
				InlineKeyboardButton(text="Категория ➡️", callback_data=f"catalog:category_switch:{category_id}:next"),
			],
			[InlineKeyboardButton(text="📦 Открыть товары", callback_data=f"catalog:open_products:{category_id}")],
			[InlineKeyboardButton(text="🏠 В меню", callback_data="catalog:back")],
		]
	)


def _product_caption(product, lang: str, currency: str, photo_index: int, photos_count: int) -> str:
	price_text = format_money_from_rub(Decimal(str(product.price)), currency)
	old_price = ""
	if product.old_price:
		old_price = f"\n<s>{format_money_from_rub(Decimal(str(product.old_price)), currency)}</s>"
	description = product.get_description(lang) or "Без описания"
	status = "✅ В наличии" if product.stock > 0 else "❌ Нет в наличии"
	return (
		f"<b>{product.get_name(lang)}</b>\n"
		f"Категория: {product.category.emoji} {product.category.get_name(lang)}\n"
		f"Цена: <b>{price_text}</b>{old_price}\n"
		f"Остаток: <b>{product.stock}</b> ({status})\n\n"
		f"{description}\n\n"
		f"Фото {photo_index + 1}/{photos_count}"
	)


async def _render_catalog(call: CallbackQuery, category_id: int, product_id: int, photo_index: int = 0) -> None:
	lang = await UserLanguage.get(call.message.chat.id)
	currency = await UserRepository.get_user_currency(call.message.chat.id)
	product = await ProductRepository.get_product_by_id(product_id)
	if not product or not product.is_active or product.category_id != category_id:
		await call.answer("Товар недоступен", show_alert=True)
		return

	photos = [photo.file_id for photo in product.photos] or ([product.photo_file_id] if product.photo_file_id else [])
	if not photos:
		media = InputMediaPhoto(media=FSInputFile(MAIN_MENU_IMAGE), caption="У этого товара пока нет фото")
		await call.message.edit_media(
			media=media,
			reply_markup=InlineKeyboardMarkup(
				inline_keyboard=[[InlineKeyboardButton(text="◀️ В меню", callback_data="catalog:back")]]
			),
		)
		return

	safe_index = photo_index % len(photos)
	caption = _product_caption(product, lang, currency, safe_index, len(photos))
	keyboard = _catalog_keyboard(category_id, product.id, safe_index, len(photos))
	media = InputMediaPhoto(media=photos[safe_index], caption=caption, parse_mode="HTML")
	await call.message.edit_media(media=media, reply_markup=keyboard)


async def _render_category(call: CallbackQuery, category_id: int) -> None:
	lang = await UserLanguage.get(call.message.chat.id)
	categories = await CategoryRepository.list_all()
	if not categories:
		await call.message.edit_media(
			media=InputMediaPhoto(media=FSInputFile(MAIN_MENU_IMAGE), caption="Каталог пока пуст"),
			reply_markup=InlineKeyboardMarkup(
				inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data="catalog:back")]]
			),
		)
		return

	ids = [item.id for item in categories]
	try:
		index = ids.index(category_id)
	except ValueError:
		index = 0

	category = categories[index]
	products = await ProductRepository.list_products_by_category(category.id, include_inactive=False)
	product_count = len(products)
	description = category.get_description(lang) or "Описание категории пока не добавлено"
	caption = (
		f"<b>{category.emoji} {category.get_name(lang)}</b>\n"
		f"Товаров: <b>{product_count}</b>\n\n"
		f"{description}"
	)

	image = category.photo_file_id or FSInputFile(FALLBACK_CATEGORY_IMAGE)
	media = InputMediaPhoto(media=image, caption=caption, parse_mode="HTML")
	await call.message.edit_media(media=media, reply_markup=_category_keyboard(category.id))


@router.callback_query(F.data == "menu:catalog")
async def show_catalog(call: CallbackQuery):
	categories = await CategoryRepository.list_all()
	if not categories:
		await call.answer()
		await call.message.edit_media(
			media=InputMediaPhoto(media=FSInputFile(MAIN_MENU_IMAGE), caption="Каталог пока пуст"),
			reply_markup=InlineKeyboardMarkup(
				inline_keyboard=[[InlineKeyboardButton(text="◀️ В меню", callback_data="catalog:back")]]
			),
		)
		return

	await call.answer()
	await _render_category(call, categories[0].id)


@router.callback_query(F.data.startswith("catalog:category_switch:"))
async def switch_category(call: CallbackQuery):
	_, _, current_category_raw, direction = call.data.split(":")
	current_id = int(current_category_raw)
	categories = await CategoryRepository.list_all()
	if not categories:
		await call.answer("Каталог пуст")
		return

	ids = [item.id for item in categories]
	try:
		current_index = ids.index(current_id)
	except ValueError:
		current_index = 0

	if direction == "next":
		target = categories[(current_index + 1) % len(categories)]
	else:
		target = categories[(current_index - 1) % len(categories)]

	await call.answer()
	await _render_category(call, target.id)


@router.callback_query(F.data.startswith("catalog:category:"))
async def back_to_category(call: CallbackQuery):
	_, _, category_id_raw = call.data.split(":")
	await call.answer()
	await _render_category(call, int(category_id_raw))


@router.callback_query(F.data.startswith("catalog:open_products:"))
async def open_category_products(call: CallbackQuery):
	category_id = int(call.data.split(":")[-1])
	products = await ProductRepository.list_products_by_category(category_id, include_inactive=False)
	if not products:
		await call.answer("В этой категории пока нет товаров", show_alert=True)
		return

	await call.answer()
	await _render_catalog(call, category_id, products[0].id, photo_index=0)


@router.callback_query(F.data.startswith("catalog:photo:"))
async def switch_product_photo(call: CallbackQuery):
	_, _, category_id_raw, product_id_raw, photo_index_raw = call.data.split(":")
	await call.answer()
	await _render_catalog(call, int(category_id_raw), int(product_id_raw), int(photo_index_raw))


@router.callback_query(F.data.startswith("catalog:product:"))
async def switch_product(call: CallbackQuery):
	_, _, category_id_raw, product_id_raw, direction = call.data.split(":")
	category_id = int(category_id_raw)
	current_id = int(product_id_raw)
	products = await ProductRepository.list_products_by_category(category_id, include_inactive=False)
	product_ids = [product.id for product in products]
	if not product_ids:
		await call.answer("В категории нет товаров")
		await _render_category(call, category_id)
		return

	try:
		current_index = product_ids.index(current_id)
	except ValueError:
		current_index = 0

	if direction == "next":
		target_index = (current_index + 1) % len(product_ids)
	else:
		target_index = (current_index - 1) % len(product_ids)

	await call.answer()
	await _render_catalog(call, category_id, product_ids[target_index], photo_index=0)


@router.callback_query(F.data.startswith("catalog:add_to_cart:"))
async def catalog_add_to_cart(call: CallbackQuery):
	from DB.repository import CartRepository, UserRepository

	product_id = int(call.data.split(":")[-1])
	product = await ProductRepository.get_product_by_id(product_id)
	if not product or not product.is_active:
		await call.answer("Товар недоступен", show_alert=True)
		return

	user = await UserRepository.get_user(call.message.chat.id)
	if not user:
		await UserRepository.create_user(call.message.chat.id, name=call.from_user.full_name or "")

	await CartRepository.add_item(call.message.chat.id, product_id, quantity=1)
	await call.answer("Товар добавлен в корзину")


@router.callback_query(F.data.startswith("catalog:buy_now:"))
async def catalog_buy_now(call: CallbackQuery, state: FSMContext):
	product_id = int(call.data.split(":")[-1])
	product = await ProductRepository.get_product_by_id(product_id)
	if not product or not product.is_active:
		await call.answer("Товар недоступен", show_alert=True)
		return

	saved_address = await UserRepository.get_user_address(call.message.chat.id)
	await state.set_state(CheckoutState.waiting_quantity)
	await state.update_data(
		mode="single",
		product_id=product_id,
		origin_message_id=call.message.message_id,
		saved_address=saved_address,
	)
	await call.answer()
	await call.message.edit_caption(
		caption=(
			"<b>Покупка товара</b>\n"
			f"{product.name}\n\n"
			"Введите количество (пример: 2)"
		),
		parse_mode="HTML",
		reply_markup=InlineKeyboardMarkup(
			inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="checkout:cancel")]]
		),
	)


@router.callback_query(F.data == "catalog:back")
async def back_to_menu_from_catalog(call: CallbackQuery):
	from app.shared.stetes import UserLanguage
	from app.shared.ui.main_menu import show_main_menu
	from core.config import settings

	lang = await UserLanguage.get(call.message.chat.id)
	await call.answer()
	await show_main_menu(
		call.bot,
		call.message.chat.id,
		lang=lang,
		message_id=call.message.message_id,
		is_admin=call.message.chat.id == settings.admin_id,
	)