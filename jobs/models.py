from django.db import models

# Create your models here.
from accounts.models import User
from companies.models import Company


class Job(models.Model):

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='jobs'
    )

    posted_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posted_jobs'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    required_skills = models.TextField()
    experience = models.IntegerField()
    location = models.CharField(max_length=255, default="Remote")
    job_type = models.CharField(max_length=100, default="Full-Time")
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.title
