from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


User = get_user_model()


class Command(BaseCommand):
    help = "Closes the specified poll for voting"

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("password")
        parser.add_argument(
            "--admin",
            action="store_true",
            default=False,
            help="Mark user as admin",
        )

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]
        as_admin = options["admin"]
        user, created = User.objects.get_or_create(
            username=username, defaults={"email": f"{username}@local.host"}
        )
        if not created:
            print(f"User {username!r} already exists")
            return

        user.set_password(password)
        if as_admin:
            user.is_superuser = True
            user.is_staff = True
        user.save()
        print(
            f"Created {'admin' if as_admin else ''} user {username!r} with password {password!r}"
        )
