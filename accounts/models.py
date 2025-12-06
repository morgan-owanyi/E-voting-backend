from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('presiding', 'Presiding Officer'),
        ('candidate', 'Candidate'),
        ('voter', 'Voter'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='voter')
    is_verified = models.BooleanField(default=False)  # OTP verification


# Create your models here.

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

