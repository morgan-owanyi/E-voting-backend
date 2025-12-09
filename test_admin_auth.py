import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import authenticate
from accounts.models import User

# Check if admin exists
user = User.objects.filter(email='admin@kuravote.com').first()
print(f"\n=== Admin User Check ===")
print(f"User exists: {user is not None}")
if user:
    print(f"Username: {user.username}")
    print(f"Email: {user.email}")
    print(f"Role: {user.role}")
    print(f"Is superuser: {user.is_superuser}")
    print(f"Is staff: {user.is_staff}")
    print(f"Is active: {user.is_active}")
    
    # Test password
    password_check = user.check_password('Admin@123456')
    print(f"Password check: {password_check}")
    
    # Test authentication
    print(f"\n=== Authentication Test ===")
    auth_result = authenticate(email='admin@kuravote.com', password='Admin@123456')
    print(f"Auth result: {auth_result}")
    print(f"Auth successful: {auth_result is not None}")
    
    # Test with request
    auth_result2 = authenticate(request=None, email='admin@kuravote.com', password='Admin@123456')
    print(f"Auth with request=None: {auth_result2 is not None}")
else:
    print("Admin user does not exist!")
    print("\nAll users in database:")
    for u in User.objects.all():
        print(f"  - {u.username} ({u.email}) - {u.role}")
