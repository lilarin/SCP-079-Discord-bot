from tortoise import fields
from tortoise.models import Model

from app.core.enums import ItemType


class User(Model):
    id = fields.IntField(pk=True)
    user_id = fields.BigIntField(unique=True)
    dossier = fields.TextField(null=True)
    balance = fields.BigIntField(default=0)
    reputation = fields.BigIntField(default=0)

    equipped_card = fields.ForeignKeyField(
        "models.Item", related_name="equipped_by", null=True, on_delete=fields.SET_NULL
    )

    inventory: fields.ManyToManyRelation["Item"] = fields.ManyToManyField(
        "models.Item", related_name="owners", through="users_items"
    )

    achievements: fields.ManyToManyRelation["Achievement"] = fields.ManyToManyField(
        "models.Achievement", related_name="users", through="users_achievements"
    )

    class Meta:
        table = "users"
        indexes = ("balance", "reputation")
        db_constraints = {
            "balance_gte_zero": "CHECK (balance >= 0)",
            "reputation_gte_zero": "CHECK (reputation >= 0)"
        }

    def __str__(self):
        return f"User {self.user_id}"

    async def set_balance(self, amount: int):
        if amount < 0:
            raise ValueError("Баланс не може бути від'ємним")
        self.balance = amount
        await self.save()

    async def set_reputation(self, amount: int):
        if amount < 0:
            raise ValueError("Репутація не може бути від'ємною")
        self.reputation = amount
        await self.save()

    async def update_balance(self, amount: int):
        new_balance = self.balance + amount
        self.balance = max(new_balance, 0)

        if amount > 0:
            self.reputation += amount

        await self.save()


class Item(Model):
    id = fields.IntField(pk=True)
    item_id = fields.CharField(max_length=50, unique=True)
    name = fields.CharField(max_length=100)
    description = fields.TextField()
    price = fields.BigIntField()
    item_type = fields.CharEnumField(ItemType)
    quantity = fields.IntField(default=0)

    class Meta:
        table = "items"
        indexes = ("price",)
        db_constraints = {
            "quantity_gte_zero": "CHECK (quantity >= 0)"
        }

    def __str__(self):
        return f"{self.name} (Qty: {self.quantity})"


class Achievement(Model):
    id = fields.IntField(pk=True)
    achievement_id = fields.CharField(max_length=50, unique=True)
    name = fields.CharField(max_length=100)
    description = fields.TextField()
    icon = fields.CharField(max_length=10, default="🏆")

    class Meta:
        table = "achievements"
        indexes = ("achievement_id",)

    def __str__(self):
        return f"{self.name}"


class SCPObject(Model):
    id = fields.IntField(pk=True)
    number = fields.CharField(max_length=255)
    title = fields.CharField(max_length=255)
    range = fields.IntField()
    object_class = fields.CharField(null=True, max_length=255)
    link = fields.CharField(unique=True, max_length=255)

    class Meta:
        table = "scp_objects"
        indexes = ("range", "object_class")

    def __str__(self):
        return f"{self.title} ({self.object_class})"


class ViewedScpObject(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="viewed_objects")
    scp_object = fields.ForeignKeyField("models.SCPObject", related_name="viewed_by_users")
    viewed_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "viewed_scp_objects"
        unique_together = ("user", "scp_object")

    def __str__(self):
        return f"User {self.user} viewed SCP {self.scp_object} at {self.viewed_at}"
