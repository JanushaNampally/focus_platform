import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'focus_platform.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import Profile

# Delete existing user if any
User.objects.filter(username='jannu').delete()

# Create superuser
user = User.objects.create_superuser(
    username='jannu',
    email='janushanampally@gmail.com',
    password='Jannu@123'
)

# Create profile
Profile.objects.get_or_create(user=user)

print("=" * 70)
print("✓ USER ACCOUNT CREATED SUCCESSFULLY!")
print("=" * 70)
print(f"Username: jannu")
print(f"Password: Jannu@123")
print(f"Email: jannu@focustube.local")
print(f"Role: Superuser (Admin access)")
print("=" * 70)
print("\nTry logging in with these credentials at:")
print("• http://localhost:8000/users/login/")
print("• Admin panel: http://localhost:8000/admin/")
print("=" * 70)
