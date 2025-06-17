from tortoise.models import Model
from tortoise import fields


class User(Model):
    id = fields.IntField(pk=True)
    user_id = fields.BigIntField(unique=True)
    dossier = fields.TextField(null=True)

    class Meta:
        table = "users"

    def __str__(self):
        return f"User {self.user_id}"