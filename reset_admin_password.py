import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounts.models import User

# Get admin user
user = User.objects.get(email='admin@kuravote.com')
print(f"Current admin: {user.username}")

# Set new password
user.set_password('Admin@123456')
user.save()

print("Password updated successfully!")

# Verify
if user.check_password('Admin@123456'):
    print("✓ Password verification successful!")
else:
    print("✗ Password verification failed!")
