from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)

from DB.repository import CategoryRepository, ProductRepository
from app.shared.stetes import AdminCategoryCreate, AdminProductCreate, UserLanguage
from app.shared.ui.main_menu import show_main_menu
from core.config import settings


router = Router(name="admin")
MAIN_MENU_IMAGE = "./publick/images/main_menu.png"
SKIP_VALUE = "-"


def _admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать категорию", callback_data="admin:create_category")],
            [InlineKeyboardButton(text="📦 Создать товар", callback_data="admin:create_product")],
            [InlineKeyboardButton(text="🧾 Управление товарами", callback_data="admin:products")],
            [InlineKeyboardButton(text="🗂 Управление категориями", callback_data="admin:categories")],
            [InlineKeyboardButton(text="◀️ В меню", callback_data="admin:back_menu")],
        ]
    )


def _is_admin(user_id: int) -> bool:
    return user_id == settings.admin_id


async def _render_panel(call: CallbackQuery, text: str) -> None:
    media = InputMediaPhoto(media=FSInputFile(MAIN_MENU_IMAGE), caption=text, parse_mode="HTML")
    await call.message.edit_media(media=media, reply_markup=_admin_panel_keyboard())


async def _update_form_message(
    call: CallbackQuery | Message,
    text: str,
    keyboard: InlineKeyboardMarkup | None = None,
    message_id: int | None = None,
) -> None:
    target_message_id = message_id or (
        call.message.message_id if isinstance(call, CallbackQuery) else None
    )

    if not target_message_id:
        return

    await call.bot.edit_message_caption(
        chat_id=call.chat.id if isinstance(call, Message) else call.message.chat.id,
        message_id=target_message_id,
        caption=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


def _categories_keyboard(categories) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{category.emoji} {category.name}",
                callback_data=f"admin:pick_category:{category.id}",
            )
        ]
        for category in categories
    ]
    rows.append([InlineKeyboardButton(text="➕ Новая категория", callback_data="admin:create_category")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _active_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Активный", callback_data="admin:active:1"),
                InlineKeyboardButton(text="⛔ Скрытый", callback_data="admin:active:0"),
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:cancel")],
        ]
    )


def _photos_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data="admin:photos_done")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:cancel")],
        ]
    )


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💾 Сохранить", callback_data="admin:confirm_save_product")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:cancel")],
        ]
    )


def _admin_product_nav_keyboard(product_id: int, photo_index: int, photos_count: int, is_active: bool):
    prev_photo = (photo_index - 1) % photos_count
    next_photo = (photo_index + 1) % photos_count
    active_label = "⛔ Скрыть" if is_active else "✅ Показать"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Товар", callback_data=f"admin:products:switch:{product_id}:prev"),
                InlineKeyboardButton(text="Товар ➡️", callback_data=f"admin:products:switch:{product_id}:next"),
            ],
            [
                InlineKeyboardButton(text="◀️ Фото", callback_data=f"admin:products:photo:{product_id}:{prev_photo}"),
                InlineKeyboardButton(text="Фото ▶️", callback_data=f"admin:products:photo:{product_id}:{next_photo}"),
            ],
            [InlineKeyboardButton(text=active_label, callback_data=f"admin:products:toggle:{product_id}")],
            [InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"admin:products:delete:{product_id}")],
            [InlineKeyboardButton(text="◀️ В админ-панель", callback_data="admin:panel")],
        ]
    )


def _admin_category_nav_keyboard(category_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Категория", callback_data=f"admin:categories:switch:{category_id}:prev"),
                InlineKeyboardButton(text="Категория ➡️", callback_data=f"admin:categories:switch:{category_id}:next"),
            ],
            [InlineKeyboardButton(text="🗑 Удалить категорию", callback_data=f"admin:categories:delete:{category_id}")],
            [InlineKeyboardButton(text="◀️ В админ-панель", callback_data="admin:panel")],
        ]
    )


def _confirm_delete_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"admin:products:delete_confirm:{product_id}")],
            [InlineKeyboardButton(text="↩️ Отмена", callback_data=f"admin:products:refresh:{product_id}")],
        ]
    )


def _confirm_delete_category_keyboard(category_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"admin:categories:delete_confirm:{category_id}")],
            [InlineKeyboardButton(text="↩️ Отмена", callback_data=f"admin:categories:refresh:{category_id}")],
        ]
    )


def _normalize_optional(value: str) -> str | None:
    value = value.strip()
    return None if value == SKIP_VALUE else value


def _product_preview_text(data: dict) -> str:
    description = data.get("description") or "Без описания"
    old_price = data.get("old_price") or "-"
    status = "✅ Активный" if data.get("is_active") else "⛔ Скрытый"

    return (
        "<b>Проверьте товар перед сохранением</b>\n\n"
        f"Категория ID: <b>{data['category_id']}</b>\n"
        f"Название: <b>{data['name']}</b>\n"
        f"Цена: <b>{data['price']}</b>\n"
        f"Старая цена: <b>{old_price}</b>\n"
        f"Остаток: <b>{data['stock']}</b>\n"
        f"Статус: {status}\n"
        f"Фото: <b>{len(data.get('photo_ids', []))}</b>\n\n"
        f"Описание: {description}"
    )


async def _render_admin_product_view(call: CallbackQuery, product_id: int, photo_index: int = 0) -> None:
    products = await ProductRepository.list_products(include_inactive=True)
    if not products:
        await _render_panel(call, "В базе пока нет товаров")
        return

    ids = [item.id for item in products]
    try:
        current_position = ids.index(product_id)
    except ValueError:
        current_position = 0

    product = products[current_position]
    photos = [photo.file_id for photo in product.photos] or ([product.photo_file_id] if product.photo_file_id else [])
    if not photos:
        await call.message.edit_caption(caption="У товара нет фото", reply_markup=None)
        return

    safe_index = photo_index % len(photos)
    status = "✅ Активен" if product.is_active else "⛔ Скрыт"
    old_price = f"\n<s>{product.old_price}</s>" if product.old_price else ""
    caption = (
        f"<b>{product.name}</b>\n"
        f"ID: <b>{product.id}</b>\n"
        f"Категория: {product.category.emoji} {product.category.name}\n"
        f"Цена: <b>{product.price}</b>{old_price}\n"
        f"Остаток: <b>{product.stock}</b>\n"
        f"Статус: {status}\n\n"
        f"Фото {safe_index + 1}/{len(photos)}"
    )
    keyboard = _admin_product_nav_keyboard(product.id, safe_index, len(photos), product.is_active)
    media = InputMediaPhoto(media=photos[safe_index], caption=caption, parse_mode="HTML")
    await call.message.edit_media(media=media, reply_markup=keyboard)


async def _render_admin_category_view(call: CallbackQuery, category_id: int) -> None:
    categories = await CategoryRepository.list_all()
    if not categories:
        await _render_panel(call, "В базе пока нет категорий")
        return

    ids = [item.id for item in categories]
    try:
        current_position = ids.index(category_id)
    except ValueError:
        current_position = 0

    category = categories[current_position]
    products = await ProductRepository.list_products_by_category(category.id, include_inactive=True)
    description = category.description or "Без описания"
    caption = (
        f"<b>{category.emoji} {category.name}</b>\n"
        f"ID: <b>{category.id}</b>\n"
        f"Sort: <b>{category.sort_order}</b>\n"
        f"Товаров: <b>{len(products)}</b>\n\n"
        f"{description}"
    )
    media = InputMediaPhoto(
        media=category.photo_file_id or FSInputFile(MAIN_MENU_IMAGE),
        caption=caption,
        parse_mode="HTML",
    )
    await call.message.edit_media(media=media, reply_markup=_admin_category_nav_keyboard(category.id))


@router.callback_query(F.data == "admin:panel")
async def admin_panel(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    await state.clear()
    await call.answer()
    await _render_panel(call, "<b>Админ-панель</b>\nВыберите действие")


@router.callback_query(F.data == "admin:back_menu")
async def admin_back_to_menu(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    await state.clear()
    lang = await UserLanguage.get(call.message.chat.id)
    await call.answer()
    await show_main_menu(
        call.bot,
        call.message.chat.id,
        lang=lang,
        message_id=call.message.message_id,
        is_admin=True,
    )


@router.callback_query(F.data == "admin:cancel")
async def admin_cancel_any_flow(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    await state.clear()
    await call.answer("Отменено")
    await _render_panel(call, "<b>Админ-панель</b>\nВыберите действие")


@router.callback_query(F.data == "admin:create_category")
async def admin_start_create_category(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    await state.set_state(AdminCategoryCreate.waiting_name)
    await state.update_data(form_message_id=call.message.message_id)
    await call.answer()
    await _update_form_message(call, "Введите название категории")


@router.message(AdminCategoryCreate.waiting_name)
async def admin_category_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminCategoryCreate.waiting_name_en)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Введите название категории на EN или '-' чтобы пропустить",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminCategoryCreate.waiting_name_en)
async def admin_category_name_en(message: Message, state: FSMContext):
    await state.update_data(name_en=_normalize_optional(message.text))
    await state.set_state(AdminCategoryCreate.waiting_name_uz)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Введите название категории на UZ или '-' чтобы пропустить",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminCategoryCreate.waiting_name_uz)
async def admin_category_name_uz(message: Message, state: FSMContext):
    await state.update_data(name_uz=_normalize_optional(message.text))
    await state.set_state(AdminCategoryCreate.waiting_description)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Введите описание категории (RU) или '-' чтобы пропустить",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminCategoryCreate.waiting_description)
async def admin_category_description(message: Message, state: FSMContext):
    await state.update_data(description=_normalize_optional(message.text))
    await state.set_state(AdminCategoryCreate.waiting_description_en)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Введите описание категории (EN) или '-' чтобы пропустить",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminCategoryCreate.waiting_description_en)
async def admin_category_description_en(message: Message, state: FSMContext):
    await state.update_data(description_en=_normalize_optional(message.text))
    await state.set_state(AdminCategoryCreate.waiting_description_uz)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Введите описание категории (UZ) или '-' чтобы пропустить",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminCategoryCreate.waiting_description_uz)
async def admin_category_description_uz(message: Message, state: FSMContext):
    await state.update_data(description_uz=_normalize_optional(message.text))
    await state.set_state(AdminCategoryCreate.waiting_photo)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Отправьте фото категории или '-' чтобы пропустить",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminCategoryCreate.waiting_photo, F.photo)
async def admin_category_photo(message: Message, state: FSMContext):
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await state.set_state(AdminCategoryCreate.waiting_emoji)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Введите emoji категории или '-' для значения по умолчанию 🛍",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminCategoryCreate.waiting_photo)
async def admin_category_photo_skip(message: Message, state: FSMContext):
    if message.text and message.text.strip() == SKIP_VALUE:
        await state.update_data(photo_file_id=None)
        await state.set_state(AdminCategoryCreate.waiting_emoji)
        data = await state.get_data()
        await _update_form_message(
            message,
            "Введите emoji категории или '-' для значения по умолчанию 🛍",
            message_id=data.get("form_message_id"),
        )
        return

    data = await state.get_data()
    await _update_form_message(
        message,
        "Нужно отправить фото категории или '-'",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminCategoryCreate.waiting_emoji)
async def admin_category_emoji(message: Message, state: FSMContext):
    emoji = message.text.strip()
    await state.update_data(emoji="🛍" if emoji == SKIP_VALUE else emoji)
    await state.set_state(AdminCategoryCreate.waiting_sort_order)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Введите sort_order (число) или '-' для 0",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminCategoryCreate.waiting_sort_order)
async def admin_category_sort_order(message: Message, state: FSMContext):
    value = message.text.strip()
    if value == SKIP_VALUE:
        sort_order = 0
    else:
        try:
            sort_order = int(value)
        except ValueError:
            data = await state.get_data()
            await _update_form_message(
                message,
                "sort_order должен быть числом. Введите еще раз",
                message_id=data.get("form_message_id"),
            )
            return

    data = await state.get_data()
    await CategoryRepository.create_category(
        name=data["name"],
        name_en=data.get("name_en"),
        name_uz=data.get("name_uz"),
        description=data.get("description"),
        description_en=data.get("description_en"),
        description_uz=data.get("description_uz"),
        photo_file_id=data.get("photo_file_id"),
        emoji=data.get("emoji", "🛍"),
        sort_order=sort_order,
    )
    await state.clear()
    await _update_form_message(
        message,
        "✅ Категория создана\n\n<b>Админ-панель</b>\nВыберите действие",
        keyboard=_admin_panel_keyboard(),
        message_id=data.get("form_message_id"),
    )


@router.callback_query(F.data == "admin:create_product")
async def admin_start_create_product(call: CallbackQuery, state: FSMContext):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    categories = await CategoryRepository.list_all()
    if not categories:
        await call.answer()
        await _update_form_message(
            call,
            "Сначала создайте хотя бы одну категорию",
            keyboard=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Создать категорию", callback_data="admin:create_category")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin:panel")],
                ]
            ),
        )
        return

    await state.set_state(AdminProductCreate.waiting_category)
    await state.update_data(form_message_id=call.message.message_id)
    await call.answer()
    await _update_form_message(call, "Выберите категорию товара", keyboard=_categories_keyboard(categories))


@router.callback_query(AdminProductCreate.waiting_category, F.data.startswith("admin:pick_category:"))
async def admin_product_pick_category(call: CallbackQuery, state: FSMContext):
    category_id = int(call.data.split(":")[-1])
    await state.update_data(category_id=category_id)
    await state.set_state(AdminProductCreate.waiting_name)
    await call.answer()
    await _update_form_message(call, "Введите название товара", keyboard=None)


@router.message(AdminProductCreate.waiting_name)
async def admin_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminProductCreate.waiting_name_en)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Название товара на EN или '-' для пропуска",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminProductCreate.waiting_name_en)
async def admin_product_name_en(message: Message, state: FSMContext):
    await state.update_data(name_en=_normalize_optional(message.text))
    await state.set_state(AdminProductCreate.waiting_name_uz)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Название товара на UZ или '-' для пропуска",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminProductCreate.waiting_name_uz)
async def admin_product_name_uz(message: Message, state: FSMContext):
    await state.update_data(name_uz=_normalize_optional(message.text))
    await state.set_state(AdminProductCreate.waiting_description)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Описание (RU) или '-' для пропуска",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminProductCreate.waiting_description)
async def admin_product_description(message: Message, state: FSMContext):
    await state.update_data(description=_normalize_optional(message.text))
    await state.set_state(AdminProductCreate.waiting_description_en)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Описание (EN) или '-' для пропуска",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminProductCreate.waiting_description_en)
async def admin_product_description_en(message: Message, state: FSMContext):
    await state.update_data(description_en=_normalize_optional(message.text))
    await state.set_state(AdminProductCreate.waiting_description_uz)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Описание (UZ) или '-' для пропуска",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminProductCreate.waiting_description_uz)
async def admin_product_description_uz(message: Message, state: FSMContext):
    await state.update_data(description_uz=_normalize_optional(message.text))
    await state.set_state(AdminProductCreate.waiting_price)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Введите цену (например 129.99)",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminProductCreate.waiting_price)
async def admin_product_price(message: Message, state: FSMContext):
    raw = message.text.strip().replace(",", ".")
    try:
        price = Decimal(raw)
    except InvalidOperation:
        data = await state.get_data()
        await _update_form_message(
            message,
            "Цена должна быть числом. Пример: 129.99",
            message_id=data.get("form_message_id"),
        )
        return

    await state.update_data(price=str(price))
    await state.set_state(AdminProductCreate.waiting_old_price)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Введите старую цену или '-' для пропуска",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminProductCreate.waiting_old_price)
async def admin_product_old_price(message: Message, state: FSMContext):
    raw = message.text.strip()
    if raw == SKIP_VALUE:
        old_price = None
    else:
        try:
            old_price = str(Decimal(raw.replace(",", ".")))
        except InvalidOperation:
            data = await state.get_data()
            await _update_form_message(
                message,
                "Старая цена должна быть числом или '-'",
                message_id=data.get("form_message_id"),
            )
            return

    await state.update_data(old_price=old_price)
    await state.set_state(AdminProductCreate.waiting_stock)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Введите остаток на складе (целое число)",
        message_id=data.get("form_message_id"),
    )


@router.message(AdminProductCreate.waiting_stock)
async def admin_product_stock(message: Message, state: FSMContext):
    try:
        stock = int(message.text.strip())
        if stock < 0:
            raise ValueError
    except ValueError:
        data = await state.get_data()
        await _update_form_message(
            message,
            "Остаток должен быть целым неотрицательным числом",
            message_id=data.get("form_message_id"),
        )
        return

    await state.update_data(stock=stock)
    await state.set_state(AdminProductCreate.waiting_is_active)
    data = await state.get_data()
    await _update_form_message(
        message,
        "Выберите статус товара",
        keyboard=_active_keyboard(),
        message_id=data.get("form_message_id"),
    )


@router.callback_query(AdminProductCreate.waiting_is_active, F.data.startswith("admin:active:"))
async def admin_product_is_active(call: CallbackQuery, state: FSMContext):
    is_active = call.data.endswith(":1")
    await state.update_data(is_active=is_active, photo_ids=[])
    await state.set_state(AdminProductCreate.waiting_photos)
    await call.answer()
    await _update_form_message(
        call,
        "Отправьте фото товара по одному (1..N). Когда закончите, нажмите 'Готово'",
        keyboard=_photos_keyboard(),
    )


@router.message(AdminProductCreate.waiting_photos, F.photo)
async def admin_product_add_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photo_ids = data.get("photo_ids", [])
    photo_ids.append(message.photo[-1].file_id)
    await state.update_data(photo_ids=photo_ids)

    await _update_form_message(
        message,
        f"Фото добавлено: <b>{len(photo_ids)}</b>\nОтправьте еще или нажмите 'Готово'",
        keyboard=_photos_keyboard(),
        message_id=data.get("form_message_id"),
    )


@router.callback_query(AdminProductCreate.waiting_photos, F.data == "admin:photos_done")
async def admin_product_photos_done(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photo_ids", [])
    if not photos:
        await call.answer("Добавьте хотя бы 1 фото", show_alert=True)
        return

    await state.set_state(AdminProductCreate.waiting_confirm)
    await call.answer()
    await _update_form_message(call, _product_preview_text(data), keyboard=_confirm_keyboard())


@router.callback_query(AdminProductCreate.waiting_confirm, F.data == "admin:confirm_save_product")
async def admin_product_confirm_save(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    product = await ProductRepository.create_product(
        category_id=data["category_id"],
        name=data["name"],
        name_en=data.get("name_en"),
        name_uz=data.get("name_uz"),
        description=data.get("description"),
        description_en=data.get("description_en"),
        description_uz=data.get("description_uz"),
        price=Decimal(data["price"]),
        old_price=Decimal(data["old_price"]) if data.get("old_price") else None,
        stock=data["stock"],
        is_active=data["is_active"],
        photo_ids=data.get("photo_ids", []),
    )

    await state.clear()
    first_photo = product.photo_file_id or data["photo_ids"][0]
    media = InputMediaPhoto(
        media=first_photo,
        caption=f"✅ Товар <b>{product.name}</b> создан\nID: <b>{product.id}</b>",
        parse_mode="HTML",
    )
    await call.answer("Сохранено")
    await call.message.edit_media(
        media=media,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Еще товар", callback_data="admin:create_product")],
                [InlineKeyboardButton(text="◀️ В админ-панель", callback_data="admin:panel")],
            ]
        ),
    )


@router.callback_query(F.data == "admin:products")
async def admin_products_start(call: CallbackQuery):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    products = await ProductRepository.list_products(include_inactive=True)
    if not products:
        await call.answer()
        await _render_panel(call, "В базе пока нет товаров")
        return

    await call.answer()
    await _render_admin_product_view(call, products[0].id, photo_index=0)


@router.callback_query(F.data.startswith("admin:products:delete:"))
async def admin_products_delete_ask(call: CallbackQuery):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    product_id = int(call.data.split(":")[-1])
    product = await ProductRepository.get_product_by_id(product_id)
    if not product:
        await call.answer("Товар не найден", show_alert=True)
        return

    await call.answer()
    await call.message.edit_reply_markup(reply_markup=_confirm_delete_product_keyboard(product_id))


@router.callback_query(F.data.startswith("admin:products:delete_confirm:"))
async def admin_products_delete_confirm(call: CallbackQuery):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    product_id = int(call.data.split(":")[-1])
    deleted = await ProductRepository.delete_product(product_id)
    if not deleted:
        await call.answer("Товар не найден", show_alert=True)
        await _render_panel(call, "<b>Админ-панель</b>\nВыберите действие")
        return

    products = await ProductRepository.list_products(include_inactive=True)
    await call.answer("Товар удален")
    if not products:
        await _render_panel(call, "Товар удален. В базе больше нет товаров")
        return

    await _render_admin_product_view(call, products[0].id, photo_index=0)


@router.callback_query(F.data.startswith("admin:products:refresh:"))
async def admin_products_refresh(call: CallbackQuery):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    product_id = int(call.data.split(":")[-1])
    await call.answer()
    await _render_admin_product_view(call, product_id, photo_index=0)


@router.callback_query(F.data == "admin:categories")
async def admin_categories_start(call: CallbackQuery):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    categories = await CategoryRepository.list_all()
    if not categories:
        await call.answer()
        await _render_panel(call, "В базе пока нет категорий")
        return

    await call.answer()
    await _render_admin_category_view(call, categories[0].id)


@router.callback_query(F.data.startswith("admin:categories:switch:"))
async def admin_categories_switch(call: CallbackQuery):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    _, _, _, category_id_raw, direction = call.data.split(":")
    current_id = int(category_id_raw)
    categories = await CategoryRepository.list_all()
    if not categories:
        await call.answer("Категорий нет")
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
    await _render_admin_category_view(call, target.id)


@router.callback_query(F.data.startswith("admin:categories:delete:"))
async def admin_categories_delete_ask(call: CallbackQuery):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    category_id = int(call.data.split(":")[-1])
    category = await CategoryRepository.get_by_id(category_id)
    if not category:
        await call.answer("Категория не найдена", show_alert=True)
        return

    await call.answer()
    await call.message.edit_reply_markup(reply_markup=_confirm_delete_category_keyboard(category_id))


@router.callback_query(F.data.startswith("admin:categories:delete_confirm:"))
async def admin_categories_delete_confirm(call: CallbackQuery):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    category_id = int(call.data.split(":")[-1])
    deleted = await CategoryRepository.delete_category(category_id)
    if not deleted:
        await call.answer("Категория не найдена", show_alert=True)
        await _render_panel(call, "<b>Админ-панель</b>\nВыберите действие")
        return

    categories = await CategoryRepository.list_all()
    await call.answer("Категория удалена")
    if not categories:
        await _render_panel(call, "Категория удалена. В базе больше нет категорий")
        return

    await _render_admin_category_view(call, categories[0].id)


@router.callback_query(F.data.startswith("admin:categories:refresh:"))
async def admin_categories_refresh(call: CallbackQuery):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    category_id = int(call.data.split(":")[-1])
    await call.answer()
    await _render_admin_category_view(call, category_id)


@router.callback_query(F.data.startswith("admin:products:photo:"))
async def admin_products_photo_switch(call: CallbackQuery):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    _, _, _, product_id_raw, photo_index_raw = call.data.split(":")
    await call.answer()
    await _render_admin_product_view(call, int(product_id_raw), int(photo_index_raw))


@router.callback_query(F.data.startswith("admin:products:switch:"))
async def admin_products_switch(call: CallbackQuery):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    _, _, _, product_id_raw, direction = call.data.split(":")
    current_id = int(product_id_raw)

    products = await ProductRepository.list_products(include_inactive=True)
    if not products:
        await call.answer("Товаров нет")
        return

    ids = [item.id for item in products]
    try:
        current_index = ids.index(current_id)
    except ValueError:
        current_index = 0

    if direction == "next":
        target = products[(current_index + 1) % len(products)]
    else:
        target = products[(current_index - 1) % len(products)]

    await call.answer()
    await _render_admin_product_view(call, target.id, photo_index=0)


@router.callback_query(F.data.startswith("admin:products:toggle:"))
async def admin_products_toggle_active(call: CallbackQuery):
    if not _is_admin(call.message.chat.id):
        await call.answer("Недостаточно прав", show_alert=True)
        return

    product_id = int(call.data.split(":")[-1])
    product = await ProductRepository.get_product_by_id(product_id)
    if not product:
        await call.answer("Товар не найден", show_alert=True)
        return

    updated = await ProductRepository.set_active(product_id, not product.is_active)
    await call.answer("Статус обновлен")
    await _render_admin_product_view(call, updated.id if updated else product_id, photo_index=0)
