from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator

class User(AbstractUser):

    username = None   # ❌ remove username

    email = models.EmailField(unique=True)

    name = models.CharField(max_length=100)

    phone = models.CharField(
        max_length=10,
        validators=[
            RegexValidator(
                regex=r'^[6-9]\d{9}$',
                message="Phone number must be valid"
            )
        ]
    )

    ROLE_CHOICES = (
        ('candidate', 'Candidate'),
        ('hr', 'HR'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    USERNAME_FIELD = 'email'     # 🔥 login using email
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email