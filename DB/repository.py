from decimal import Decimal

from DB.models import CartItem, Category, Order, OrderItem, Product, ProductPhoto, User


class UserRepository:
    @staticmethod
    async def get_user(user_id: int) -> User | None:
        return await User.get_or_none(id=user_id)

    @staticmethod
    async def create_user(user_id: int, name: str = "", language: str = "ru") -> User:
        return await User.create(id=user_id, name=name, language=language, currency="rub")

    @staticmethod
    async def set_user_language(user_id: int, language: str) -> User:
        user, created = await User.get_or_create(
            id=user_id, defaults={"language": language, "name": "", "currency": "rub"}
        )
        if not created and user.language != language:
            user.language = language
            await user.save(update_fields=["language"])
        return user

    @staticmethod
    async def set_user_address(user_id: int, address: str) -> User:
        user, _ = await User.get_or_create(id=user_id, defaults={"name": "", "currency": "rub"})
        user.default_address = address
        await user.save(update_fields=["default_address"])
        return user

    @staticmethod
    async def set_user_currency(user_id: int, currency: str) -> User:
        user, _ = await User.get_or_create(id=user_id, defaults={"name": "", "currency": "rub"})
        user.currency = currency
        user.currency_selected = True
        await user.save(update_fields=["currency", "currency_selected"])
        return user

    @staticmethod
    async def get_user_currency(user_id: int) -> str:
        user = await UserRepository.get_user(user_id)
        return user.currency if user and user.currency else "rub"

    @staticmethod
    async def get_user_address(user_id: int) -> str | None:
        user = await UserRepository.get_user(user_id)
        return user.default_address if user else None


class CategoryRepository:
    @staticmethod
    async def list_all() -> list[Category]:
        return await Category.all().order_by("sort_order", "id")

    @staticmethod
    async def create_category(
        name: str,
        emoji: str = "🛍",
        name_en: str | None = None,
        name_uz: str | None = None,
        description: str | None = None,
        description_en: str | None = None,
        description_uz: str | None = None,
        photo_file_id: str | None = None,
        sort_order: int = 0,
    ) -> Category:
        return await Category.create(
            name=name,
            emoji=emoji,
            name_en=name_en,
            name_uz=name_uz,
            description=description,
            description_en=description_en,
            description_uz=description_uz,
            photo_file_id=photo_file_id,
            sort_order=sort_order,
        )

    @staticmethod
    async def get_by_id(category_id: int) -> Category | None:
        return await Category.get_or_none(id=category_id)

    @staticmethod
    async def delete_category(category_id: int) -> bool:
        product_ids = await Product.filter(category_id=category_id).values_list("id", flat=True)
        if product_ids:
            await ProductPhoto.filter(product_id__in=list(product_ids)).delete()
            await Product.filter(id__in=list(product_ids)).delete()
        deleted_count = await Category.filter(id=category_id).delete()
        return deleted_count > 0


class ProductRepository:
    @staticmethod
    async def create_product(
        category_id: int,
        name: str,
        price: Decimal,
        stock: int,
        is_active: bool,
        photo_ids: list[str],
        name_en: str | None = None,
        name_uz: str | None = None,
        description: str | None = None,
        description_en: str | None = None,
        description_uz: str | None = None,
        old_price: Decimal | None = None,
    ) -> Product:
        product = await Product.create(
            category_id=category_id,
            name=name,
            name_en=name_en,
            name_uz=name_uz,
            description=description,
            description_en=description_en,
            description_uz=description_uz,
            price=price,
            old_price=old_price,
            photo_file_id=photo_ids[0] if photo_ids else None,
            stock=stock,
            is_active=is_active,
        )

        if photo_ids:
            await ProductPhoto.bulk_create(
                [
                    ProductPhoto(product_id=product.id, file_id=file_id, sort_order=index)
                    for index, file_id in enumerate(photo_ids)
                ]
            )

        return await Product.get(id=product.id).select_related("category").prefetch_related("photos")

    @staticmethod
    async def list_products(include_inactive: bool = False) -> list[Product]:
        query = Product.all().select_related("category").prefetch_related("photos")
        if not include_inactive:
            query = query.filter(is_active=True)
        return await query.order_by("-created_at", "id")

    @staticmethod
    async def list_products_by_category(category_id: int, include_inactive: bool = False) -> list[Product]:
        query = (
            Product.filter(category_id=category_id)
            .select_related("category")
            .prefetch_related("photos")
        )
        if not include_inactive:
            query = query.filter(is_active=True)
        return await query.order_by("-created_at", "id")

    @staticmethod
    async def get_product_by_id(product_id: int) -> Product | None:
        return await Product.get_or_none(id=product_id).select_related("category").prefetch_related("photos")

    @staticmethod
    async def set_active(product_id: int, is_active: bool) -> Product | None:
        product = await Product.get_or_none(id=product_id)
        if not product:
            return None
        product.is_active = is_active
        await product.save(update_fields=["is_active"])
        return await ProductRepository.get_product_by_id(product_id)

    @staticmethod
    async def add_photo(product_id: int, file_id: str) -> ProductPhoto:
        last_photo = await ProductPhoto.filter(product_id=product_id).order_by("-sort_order").first()
        next_sort = (last_photo.sort_order + 1) if last_photo else 0
        photo = await ProductPhoto.create(product_id=product_id, file_id=file_id, sort_order=next_sort)

        product = await Product.get_or_none(id=product_id)
        if product and not product.photo_file_id:
            product.photo_file_id = file_id
            await product.save(update_fields=["photo_file_id"])

        return photo

    @staticmethod
    async def get_active_product_ids() -> list[int]:
        products = await Product.filter(is_active=True).order_by("-created_at", "id").values_list("id", flat=True)
        return list(products)

    @staticmethod
    async def delete_product(product_id: int) -> bool:
        await ProductPhoto.filter(product_id=product_id).delete()
        deleted_count = await Product.filter(id=product_id).delete()
        return deleted_count > 0


class CartRepository:
    @staticmethod
    async def add_item(user_id: int, product_id: int, quantity: int = 1) -> CartItem:
        item = await CartItem.get_or_none(user_id=user_id, product_id=product_id)
        if item:
            item.quantity += quantity
            await item.save(update_fields=["quantity"])
            return item
        return await CartItem.create(user_id=user_id, product_id=product_id, quantity=quantity)

    @staticmethod
    async def set_item_quantity(user_id: int, product_id: int, quantity: int) -> CartItem | None:
        item = await CartItem.get_or_none(user_id=user_id, product_id=product_id)
        if not item:
            return None
        item.quantity = quantity
        await item.save(update_fields=["quantity"])
        return item

    @staticmethod
    async def remove_item(user_id: int, product_id: int) -> bool:
        deleted_count = await CartItem.filter(user_id=user_id, product_id=product_id).delete()
        return deleted_count > 0

    @staticmethod
    async def clear(user_id: int) -> None:
        await CartItem.filter(user_id=user_id).delete()

    @staticmethod
    async def list_items(user_id: int) -> list[CartItem]:
        return await CartItem.filter(user_id=user_id).select_related("product").order_by("-id")


class OrderRepository:
    @staticmethod
    async def create_order_from_cart(user_id: int, address: str, payment_method: str) -> Order | None:
        cart_items = await CartRepository.list_items(user_id)
        if not cart_items:
            return None

        total = Decimal("0")
        order_rows: list[tuple[CartItem, Decimal, Decimal]] = []
        for item in cart_items:
            if not item.product or not item.product.is_active:
                continue
            price = Decimal(str(item.product.price))
            subtotal = price * item.quantity
            total += subtotal
            order_rows.append((item, price, subtotal))

        if not order_rows:
            return None

        order = await Order.create(
            user_id=user_id,
            address=address,
            payment_method=payment_method,
            status="new",
            total_amount=total,
        )
        await OrderItem.bulk_create(
            [
                OrderItem(
                    order_id=order.id,
                    product_id=row[0].product_id,
                    product_name=row[0].product.name,
                    price=row[1],
                    quantity=row[0].quantity,
                    subtotal=row[2],
                )
                for row in order_rows
            ]
        )
        await CartRepository.clear(user_id)
        return await Order.get(id=order.id).prefetch_related("items")

    @staticmethod
    async def create_order_single_product(
        user_id: int,
        product_id: int,
        quantity: int,
        address: str,
        payment_method: str,
    ) -> Order | None:
        product = await Product.get_or_none(id=product_id)
        if not product or not product.is_active:
            return None

        price = Decimal(str(product.price))
        subtotal = price * quantity
        order = await Order.create(
            user_id=user_id,
            address=address,
            payment_method=payment_method,
            status="new",
            total_amount=subtotal,
        )
        await OrderItem.create(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            price=price,
            quantity=quantity,
            subtotal=subtotal,
        )
        return await Order.get(id=order.id).prefetch_related("items")




async def init_db(): 
    from tortoise import Tortoise
    from core.config import settings
    import logging
  
    await Tortoise.init(
            db_url=settings.db_url, modules={"models": ["DB.models"]}
        )
    await Tortoise.generate_schemas()

    # generate_schemas не изменяет уже существующие таблицы.
    # Для старых БД добавляем новые колонки/таблицы безопасно (idempotent).
    if settings.db_url.startswith("postgres"):
        conn = Tortoise.get_connection("default")
        try:
            await conn.execute_script(
                """
                ALTER TABLE categories ADD COLUMN IF NOT EXISTS description TEXT;
                ALTER TABLE categories ADD COLUMN IF NOT EXISTS description_en TEXT;
                ALTER TABLE categories ADD COLUMN IF NOT EXISTS description_uz TEXT;
                ALTER TABLE categories ADD COLUMN IF NOT EXISTS photo_file_id VARCHAR(255);
                ALTER TABLE users ADD COLUMN IF NOT EXISTS default_address TEXT;
                ALTER TABLE users ADD COLUMN IF NOT EXISTS currency VARCHAR(8) NOT NULL DEFAULT 'rub';
                ALTER TABLE users ADD COLUMN IF NOT EXISTS currency_selected BOOLEAN NOT NULL DEFAULT FALSE;

                CREATE TABLE IF NOT EXISTS product_photos (
                    id SERIAL PRIMARY KEY,
                    product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    file_id VARCHAR(255) NOT NULL,
                    sort_order INT NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS cart_items (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    quantity INT NOT NULL DEFAULT 1,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (user_id, product_id)
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    address TEXT NOT NULL,
                    payment_method VARCHAR(32) NOT NULL DEFAULT 'cash',
                    status VARCHAR(32) NOT NULL DEFAULT 'new',
                    total_amount NUMERIC(12,2) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS order_items (
                    id SERIAL PRIMARY KEY,
                    order_id INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                    product_id INT REFERENCES products(id) ON DELETE SET NULL,
                    product_name VARCHAR(255) NOT NULL,
                    price NUMERIC(10,2) NOT NULL,
                    quantity INT NOT NULL DEFAULT 1,
                    subtotal NUMERIC(12,2) NOT NULL
                );
                """
            )
        except Exception as exc:
            logging.exception("DB startup schema sync failed: %s", exc)