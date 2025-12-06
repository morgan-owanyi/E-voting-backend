# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import random

class User(AbstractUser):
    """
    Custom user model with roles and email verification flag.
    """
    ROLE_ADMIN = "ADMIN"
    ROLE_PRESIDING = "PRESIDING_OFFICER"
    ROLE_CANDIDATE = "CANDIDATE"
    ROLE_VOTER = "VOTER"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_PRESIDING, "Presiding Officer"),
        (ROLE_CANDIDATE, "Candidate"),
        (ROLE_VOTER, "Voter"),
    ]

    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default=ROLE_VOTER)
    is_email_verified = models.BooleanField(default=False)

    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser

    def is_presiding(self):
        return self.role == self.ROLE_PRESIDING

    def __str__(self):
        return f"{self.username} ({self.role})"


class EmailOTP(models.Model):
    """
    Simple Email OTP model — will be used for verifying voters.
    """
    email = models.EmailField()
    code = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="otps")

    @classmethod
    def create_otp(cls, email, user=None, length=6, expiry_seconds=None):
        if expiry_seconds is None:
            expiry_seconds = getattr(settings, "OTP_EXPIRY_SECONDS", 600)
        code = "".join(str(random.randint(0, 9)) for _ in range(length))
        expires_at = timezone.now() + timedelta(seconds=expiry_seconds)
        return cls.objects.create(email=email, code=code, expires_at=expires_at, user=user)

    def is_valid(self):
        return (not self.used) and (timezone.now() <= self.expires_at)

    def mark_used(self):
        self.used = True
        self.save()
