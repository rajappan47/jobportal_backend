from django.db import models
from accounts.models import User


class Company(models.Model):

    company_name = models.CharField(max_length=255)

    company_email = models.EmailField(unique=True)

    company_phone = models.CharField(max_length=10)

    address = models.TextField()

    district = models.CharField(max_length=100)

    state = models.CharField(max_length=100)

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='companies'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name