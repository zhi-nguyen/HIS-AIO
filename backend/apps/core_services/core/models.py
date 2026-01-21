from django.db import models
from uuid6 import uuid7

class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    version = models.IntegerField(default=1)

    class Meta:
        abstract = True