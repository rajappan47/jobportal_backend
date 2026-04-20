from django.db import models
from accounts.models import User

class Education(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='educations'
    )

    level = models.CharField(
        max_length=20,
        choices=[
            ('pg', 'PG'),
            ('ug', 'UG'),
            ('hsc', 'HSC'),
            ('sslc', 'SSLC')
        ]
    )

    institution_name = models.CharField(max_length=255)
    degree = models.CharField(max_length=255)
    percentage = models.CharField(max_length=10)
    city = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} - {self.level}"


class CandidateProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    phone = models.CharField(max_length=10)

    skills = models.TextField()

    resume = models.FileField(upload_to='resumes/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.email