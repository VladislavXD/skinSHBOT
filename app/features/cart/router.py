from decimal import Decimal, ROUND_UP

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from DB.repository import CartRepository, OrderRepository, ProductRepository, UserRepository
from app.shared.currency import format_money_from_rub
from app.shared.stetes import CheckoutState, UserLanguage
from app.shared.ui.main_menu import show_main_menu
from core.config import settings


router = Router(name="cart")


def _cart_keyboard(items) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        rows.append(
            [
                InlineKeyboardButton(text="➖", callback_data=f"cart:qty:{item.product_id}:-1"),
                InlineKeyboardButton(text=f"{item.product.name} x{item.quantity}", callback_data="cart:noop"),
                InlineKeyboardButton(text="➕", callback_data=f"cart:qty:{item.product_id}:1"),
            ]
        )
        rows.append([InlineKeyboardButton(text="🗑 Удалить", callback_data=f"cart:remove:{item.product_id}")])

    rows.append([InlineKeyboardButton(text="✅ Оформить", callback_data="cart:checkout")])
    rows.append([InlineKeyboardButton(text="🧹 Очистить корзину", callback_data="cart:clear")])
    rows.append([InlineKeyboardButton(text="🏠 В меню", callback_data="cart:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _payment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Оплатить звездами", callback_data="checkout:pay:stars")],
            [InlineKeyboardButton(text="📦 Оформить без оплаты", callback_data="checkout:pay:cash")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="checkout:cancel")],
        ]
    )


def _stars_amount(value: Decimal) -> int:
    rounded = value.to_integral_value(rounding=ROUND_UP)
    return int(rounded)


def _address_example() -> str:
    return (
        "<b>Введите полный адрес доставки</b>\n\n"
        "Пример:\n"
        "г. Ташкент, Мирзо-Улугбекский район, ул. Амира Темура 45, "
        "подъезд 2, этаж 5, кв. 27\n\n"
        "Можно добавить ориентир и комментарий для курьера."
    )


def _address_keyboard(has_saved: bool) -> InlineKeyboardMarkup:
    rows = []
    if has_saved:
        rows.append([InlineKeyboardButton(text="📍 Использовать сохраненный адрес", callback_data="checkout:use_saved")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="checkout:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _cart_text(items, currency: str) -> str:
    total = Decimal("0")
    lines = ["<b>Ваша корзина</b>"]
    for item in items:
        subtotal = Decimal(str(item.product.price)) * item.quantity
        total += subtotal
        lines.append(f"• {item.product.name} x{item.quantity} = {format_money_from_rub(subtotal, currency)}")

    lines.append("")
    lines.append(f"Итого: <b>{format_money_from_rub(total, currency)}</b>")
    return "\n".join(lines)


async def _notify_admin_about_order(call: CallbackQuery | Message, order) -> None:
    if not settings.admin_id:
        return

    user = call.from_user
    mention = f"<a href='tg://user?id={user.id}'>{user.full_name}</a>"
    username_line = f"@{user.username}" if user.username else "без username"
    items_text = "\n".join([
        f"• {item.product_name} x{item.quantity} = {item.subtotal}" for item in order.items
    ])

    payment_label = "Звезды" if order.payment_method == "stars" else "Без оплаты/наличные"
    text = (
        "<b>Новый заказ</b>\n"
        f"Заказ ID: <b>{order.id}</b>\n"
        f"Клиент: {mention}\n"
        f"Username: {username_line}\n"
        f"Способ: <b>{payment_label}</b>\n"
        f"Адрес: {order.address}\n\n"
        f"{items_text}\n\n"
        f"Сумма: <b>{order.total_amount} RUB</b>"
    )
    await call.bot.send_message(settings.admin_id, text, parse_mode="HTML")


async def _calculate_checkout_total(user_id: int, data: dict) -> Decimal | None:
    mode = data.get("mode")
    if mode == "single":
        product = await ProductRepository.get_product_by_id(data["product_id"])
        if not product or not product.is_active:
            return None
        qty = int(data.get("quantity", 1))
        return Decimal(str(product.price)) * qty

    items = await CartRepository.list_items(user_id)
    if not items:
        return None

    total = Decimal("0")
    for item in items:
        if not item.product or not item.product.is_active:
            continue
        total += Decimal(str(item.product.price)) * item.quantity
    return total if total > 0 else None


@router.callback_query(F.data == "menu:cart")
async def show_cart(call: CallbackQuery):
    items = await CartRepository.list_items(call.message.chat.id)
    currency = await UserRepository.get_user_currency(call.message.chat.id)
    await call.answer()
    if not items:
        await call.message.edit_caption(
            caption="Корзина пуста",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data="cart:back")]]
            ),
        )
        return

    await call.message.edit_caption(
        caption=_cart_text(items, currency),
        parse_mode="HTML",
        reply_markup=_cart_keyboard(items),
    )


@router.callback_query(F.data == "cart:noop")
async def cart_noop(call: CallbackQuery):
    await call.answer()


@router.callback_query(F.data.startswith("cart:qty:"))
async def cart_change_qty(call: CallbackQuery):
    _, _, product_id_raw, delta_raw = call.data.split(":")
    product_id = int(product_id_raw)
    delta = int(delta_raw)

    items = await CartRepository.list_items(call.message.chat.id)
    target = next((i for i in items if i.product_id == product_id), None)
    if not target:
        await call.answer("Товар не найден", show_alert=True)
        return

    new_qty = target.quantity + delta
    if new_qty <= 0:
        await CartRepository.remove_item(call.message.chat.id, product_id)
    else:
        await CartRepository.set_item_quantity(call.message.chat.id, product_id, new_qty)

    await call.answer()
    currency = await UserRepository.get_user_currency(call.message.chat.id)
    items = await CartRepository.list_items(call.message.chat.id)
    if not items:
        await call.message.edit_caption(
            caption="Корзина пуста",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data="cart:back")]]
            ),
        )
        return

    await call.message.edit_caption(
        caption=_cart_text(items, currency),
        parse_mode="HTML",
        reply_markup=_cart_keyboard(items),
    )


@router.callback_query(F.data.startswith("cart:remove:"))
async def cart_remove_item(call: CallbackQuery):
    product_id = int(call.data.split(":")[-1])
    await CartRepository.remove_item(call.message.chat.id, product_id)
    await call.answer("Удалено")
    currency = await UserRepository.get_user_currency(call.message.chat.id)
    items = await CartRepository.list_items(call.message.chat.id)
    if not items:
        await call.message.edit_caption(
            caption="Корзина пуста",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data="cart:back")]]
            ),
        )
        return

    await call.message.edit_caption(
        caption=_cart_text(items, currency),
        parse_mode="HTML",
        reply_markup=_cart_keyboard(items),
    )


@router.callback_query(F.data == "cart:clear")
async def cart_clear(call: CallbackQuery):
    await CartRepository.clear(call.message.chat.id)
    await call.answer("Корзина очищена")
    await call.message.edit_caption(
        caption="Корзина пуста",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data="cart:back")]]
        ),
    )


@router.callback_query(F.data == "cart:checkout")
async def cart_checkout(call: CallbackQuery, state: FSMContext):
    items = await CartRepository.list_items(call.message.chat.id)
    if not items:
        await call.answer("Корзина пуста", show_alert=True)
        return

    saved_address = await UserRepository.get_user_address(call.message.chat.id)
    await state.set_state(CheckoutState.waiting_address)
    await state.update_data(mode="cart", origin_message_id=call.message.message_id, saved_address=saved_address)
    await call.answer()
    await call.message.edit_caption(
        caption=_address_example(),
        parse_mode="HTML",
        reply_markup=_address_keyboard(bool(saved_address)),
    )


@router.message(CheckoutState.waiting_quantity)
async def checkout_single_quantity(message: Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        if qty <= 0:
            raise ValueError
    except ValueError:
        data = await state.get_data()
        await message.bot.edit_message_caption(
            chat_id=message.chat.id,
            message_id=data.get("origin_message_id"),
            caption="Количество должно быть целым числом больше 0. Пример: 2",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="checkout:cancel")]]
            ),
        )
        return

    await state.update_data(quantity=qty)
    await state.set_state(CheckoutState.waiting_address)
    data = await state.get_data()
    await message.bot.edit_message_caption(
        chat_id=message.chat.id,
        message_id=data.get("origin_message_id"),
        caption=_address_example(),
        parse_mode="HTML",
        reply_markup=_address_keyboard(bool(data.get("saved_address"))),
    )


@router.callback_query(F.data == "checkout:use_saved")
async def checkout_use_saved(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    saved = data.get("saved_address")
    if not saved:
        await call.answer("Сохраненный адрес не найден", show_alert=True)
        return

    await state.update_data(address=saved)
    await state.set_state(CheckoutState.waiting_payment_method)
    await call.answer("Используем сохраненный адрес")
    await call.message.edit_caption(caption="Выберите финальный вариант", reply_markup=_payment_keyboard())


@router.message(CheckoutState.waiting_address)
async def checkout_address(message: Message, state: FSMContext):
    address = message.text.strip()
    if len(address) < 10:
        data = await state.get_data()
        await message.bot.edit_message_caption(
            chat_id=message.chat.id,
            message_id=data.get("origin_message_id"),
            caption="Адрес слишком короткий. Укажите полный адрес как в примере.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="checkout:cancel")]]
            ),
        )
        return

    await state.update_data(address=address)
    await UserRepository.set_user_address(message.chat.id, address)
    await state.set_state(CheckoutState.waiting_payment_method)
    data = await state.get_data()
    await message.bot.edit_message_caption(
        chat_id=message.chat.id,
        message_id=data.get("origin_message_id"),
        caption="Выберите финальный вариант",
        reply_markup=_payment_keyboard(),
    )


@router.callback_query(F.data.startswith("checkout:pay:"))
async def checkout_pay(call: CallbackQuery, state: FSMContext):
    method = call.data.split(":")[-1]
    data = await state.get_data()
    mode = data.get("mode")
    address = data.get("address")
    currency = await UserRepository.get_user_currency(call.message.chat.id)

    if method == "stars":
        total = await _calculate_checkout_total(call.message.chat.id, data)
        if not total:
            await state.clear()
            await call.answer("Не удалось подготовить оплату", show_alert=True)
            return

        stars = _stars_amount(total)
        payload = f"stars_order:{call.message.chat.id}:{call.message.message_id}"
        await state.update_data(pending_stars_payload=payload)

        await call.bot.send_invoice(
            chat_id=call.message.chat.id,
            title="Оплата заказа",
            description=f"Оплата заказа на сумму {stars} звезд",
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Заказ", amount=stars)],
            start_parameter="stars-order",
        )
        await call.answer("Счет отправлен")
        await call.message.edit_caption(
            caption=(
                "Счет на оплату звездами отправлен отдельным сообщением.\n"
                "После успешной оплаты заказ будет оформлен автоматически."
            ),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="checkout:cancel")]]
            ),
        )
        return

    if mode == "single":
        order = await OrderRepository.create_order_single_product(
            user_id=call.message.chat.id,
            product_id=data["product_id"],
            quantity=data.get("quantity", 1),
            address=address,
            payment_method=method,
        )
    else:
        order = await OrderRepository.create_order_from_cart(
            user_id=call.message.chat.id,
            address=address,
            payment_method=method,
        )

    if not order:
        await state.clear()
        await call.answer("Не удалось оформить заказ", show_alert=True)
        return

    await _notify_admin_about_order(call, order)
    await state.clear()
    payment_text = "Оплата звездами выбрана" if method == "stars" else "Заказ оформлен"
    await call.answer("Готово")
    await call.message.edit_caption(
        caption=(
            f"✅ {payment_text}\n"
            f"Заказ №{order.id} принят.\n"
            f"Сумма: {format_money_from_rub(Decimal(str(order.total_amount)), currency)}\n"
            "Админ свяжется с вами напрямую."
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data="cart:back")]]
        ),
    )


@router.pre_checkout_query()
async def process_stars_pre_checkout(pre_checkout_query: PreCheckoutQuery, state: FSMContext):
    data = await state.get_data()
    expected_payload = data.get("pending_stars_payload")
    if not expected_payload or pre_checkout_query.invoice_payload != expected_payload:
        await pre_checkout_query.answer(ok=False, error_message="Данные платежа устарели. Повторите оформление.")
        return

    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def handle_successful_stars_payment(message: Message, state: FSMContext):
    if message.successful_payment.currency != "XTR":
        return

    data = await state.get_data()
    expected_payload = data.get("pending_stars_payload")
    if not expected_payload or message.successful_payment.invoice_payload != expected_payload:
        await message.answer("Платеж получен, но данные заказа не найдены. Напишите в поддержку.")
        return

    mode = data.get("mode")
    address = data.get("address")

    if mode == "single":
        order = await OrderRepository.create_order_single_product(
            user_id=message.chat.id,
            product_id=data["product_id"],
            quantity=data.get("quantity", 1),
            address=address,
            payment_method="stars",
        )
    else:
        order = await OrderRepository.create_order_from_cart(
            user_id=message.chat.id,
            address=address,
            payment_method="stars",
        )

    if not order:
        await state.clear()
        await message.answer("Оплата прошла, но заказ не создан. Админ свяжется с вами.")
        return

    await _notify_admin_about_order(message, order)
    await state.clear()

    currency = await UserRepository.get_user_currency(message.chat.id)
    items_text = "\n".join([f"• {item.product_name} x{item.quantity}" for item in order.items])
    await message.answer(
        (
            f"✅ Оплата звездами прошла успешно\n"
            f"Заказ №{order.id} оформлен\n\n"
            f"Состав:\n{items_text}\n\n"
            f"Адрес: {order.address}\n"
            f"Сумма: {format_money_from_rub(Decimal(str(order.total_amount)), currency)}\n\n"
            "Админ свяжется с вами напрямую."
        )
    )


@router.callback_query(F.data == "checkout:cancel")
async def checkout_cancel(call: CallbackQuery, state: FSMContext):
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


@router.callback_query(F.data == "cart:back")
async def cart_back(call: CallbackQuery):
    lang = await UserLanguage.get(call.message.chat.id)
    await call.answer()
    await show_main_menu(
        call.bot,
        call.message.chat.id,
        lang=lang,
        message_id=call.message.message_id,
        is_admin=call.message.chat.id == settings.admin_id,
    )
