import sys
import django
from django.contrib.auth import get_user_model
from django.conf import settings
if not settings.configured:
    django.setup()


User = get_user_model()
user, created = User.objects.get_or_create(
    username='admin',
    defaults={'email': 'admin@local.host'}
)
if created:
    user.set_password('s3cr3t')
    user.is_superuser = True
    user.is_staff = True
    user.save()
    print(f"Created user 'admin' with password 's3cr3t'")
else:
    print("User 'admin' already exists")
