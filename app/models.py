from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.IntField(pk=True)
    user_id = fields.BigIntField(unique=True)
    dossier = fields.TextField(null=True)

    class Meta:
        table = "users"

    def __str__(self):
        return f"User {self.user_id}"


class SCPObject(Model):
    id = fields.IntField(pk=True)
    title = fields.TextField()
    range = fields.IntField()
    object_class = fields.TextField(null=True)
    link = fields.CharField(unique=True, max_length=255)

    class Meta:
        table = "scp_objects"

    def __str__(self):
        return f"{self.title} ({self.object_class})"
