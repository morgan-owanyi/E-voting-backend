import os
import django
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

print("=== Mailgun Email Test ===")
print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")

# Test sending email
try:
    result = send_mail(
        subject='Test Email from KuraVote',
        message='This is a test email to verify Mailgun configuration.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=['admin@kuravote.com'],  # Change to your email
        fail_silently=False,
    )
    print(f"\n✓ Email sent successfully! Result: {result}")
except Exception as e:
    print(f"\n✗ Email failed: {e}")
    print(f"Error type: {type(e).__name__}")
