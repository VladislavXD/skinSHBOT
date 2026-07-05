from tortoise import Model
from tortoise import fields



class User(Model):
    id = fields.BigIntField(pk=True)          # соответствует telegram user_id
    name = fields.CharField(max_length=255, default="")
    language = fields.CharField(max_length=8, default="ru")
    default_address = fields.TextField(null=True)
    currency = fields.CharField(max_length=8, default="rub")
    currency_selected = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"


class Category(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    name_en = fields.CharField(max_length=100, null=True)
    name_uz = fields.CharField(max_length=100, null=True)
    description = fields.TextField(null=True)
    description_en = fields.TextField(null=True)
    description_uz = fields.TextField(null=True)
    photo_file_id = fields.CharField(max_length=255, null=True)
    emoji = fields.CharField(max_length=8, default="🛍")
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "categories"
        ordering = ["sort_order"]

    def __str__(self):
        return self.name

    def get_name(self, lang: str) -> str:
        return getattr(self, f"name_{lang}", None) or self.name

    def get_description(self, lang: str) -> str:
        return getattr(self, f"description_{lang}", None) or self.description or ""


class Product(Model):
    id = fields.IntField(pk=True)
    category = fields.ForeignKeyField("models.Category", related_name="products")

    name = fields.CharField(max_length=255)
    name_en = fields.CharField(max_length=255, null=True)
    name_uz = fields.CharField(max_length=255, null=True)

    description = fields.TextField(null=True)
    description_en = fields.TextField(null=True)
    description_uz = fields.TextField(null=True)

    price = fields.DecimalField(max_digits=10, decimal_places=2)
    old_price = fields.DecimalField(max_digits=10, decimal_places=2, null=True)  # для скидок

    photo_file_id = fields.CharField(max_length=255, null=True)  # telegram file_id, не путь на диске
    stock = fields.IntField(default=0)       # остаток на складе

    is_active = fields.BooleanField(default=True)  # скрыть товар, не удаляя
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "products"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_name(self, lang: str) -> str:
        return getattr(self, f"name_{lang}", None) or self.name

    def get_description(self, lang: str) -> str:
        return getattr(self, f"description_{lang}", None) or self.description or ""


class ProductPhoto(Model):
    id = fields.IntField(pk=True)
    product = fields.ForeignKeyField("models.Product", related_name="photos", on_delete=fields.CASCADE)
    file_id = fields.CharField(max_length=255)
    sort_order = fields.IntField(default=0)

    class Meta:
        table = "product_photos"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"Photo<{self.id}> for product {self.product_id}"


class CartItem(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="cart_items", on_delete=fields.CASCADE)
    product = fields.ForeignKeyField("models.Product", related_name="cart_items", on_delete=fields.CASCADE)
    quantity = fields.IntField(default=1)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "cart_items"
        unique_together = (("user", "product"),)


class Order(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="orders", on_delete=fields.CASCADE)
    address = fields.TextField()
    payment_method = fields.CharField(max_length=32, default="cash")
    status = fields.CharField(max_length=32, default="new")
    total_amount = fields.DecimalField(max_digits=12, decimal_places=2)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "orders"
        ordering = ["-created_at"]


class OrderItem(Model):
    id = fields.IntField(pk=True)
    order = fields.ForeignKeyField("models.Order", related_name="items", on_delete=fields.CASCADE)
    product = fields.ForeignKeyField("models.Product", related_name="order_items", on_delete=fields.SET_NULL, null=True)
    product_name = fields.CharField(max_length=255)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    quantity = fields.IntField(default=1)
    subtotal = fields.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        table = "order_items"
