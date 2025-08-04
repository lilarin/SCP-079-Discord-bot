from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.IntField(pk=True)
    user_id = fields.BigIntField(unique=True)
    dossier = fields.CharField(null=True, max_length=255)
    balance = fields.BigIntField(default=0)
    reputation = fields.BigIntField(default=0)

    class Meta:
        table = "users"
        db_constraints = {
            "balance_gte_zero": "CHECK (balance >= 0)"
        }

    def __str__(self):
        return f"User {self.user_id}"


class SCPObject(Model):
    id = fields.IntField(pk=True)
    number = fields.CharField(max_length=255)
    title = fields.CharField(max_length=255)
    range = fields.IntField()
    object_class = fields.CharField(null=True, max_length=255)
    link = fields.CharField(unique=True, max_length=255)

    class Meta:
        table = "scp_objects"

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
