from cuid2 import Cuid
from django.contrib.auth.models import AbstractUser
from django.db import models

_cuid = Cuid()


def generate_cuid():
    return _cuid.generate()


class User(AbstractUser):
    id = models.CharField(
        primary_key=True, max_length=32, default=generate_cuid, editable=False
    )
