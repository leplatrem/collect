from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


User = get_user_model()


class Command(BaseCommand):
    help = "Create a user, optionally as admin or collector"

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("password")
        parser.add_argument(
            "--admin",
            action="store_true",
            default=False,
            help="Mark user as admin (superuser + staff)",
        )
        parser.add_argument(
            "--collector",
            action="store_true",
            default=False,
            help="Add user to the collectors group (can CRUD collectables)",
        )

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]
        as_admin = options["admin"]
        as_collector = options["collector"]

        user, created = User.objects.get_or_create(
            username=username, defaults={"email": f"{username}@local.host"}
        )
        if not created:
            self.stdout.write(f"User {username!r} already exists")
            return

        user.set_password(password)
        if as_admin:
            user.is_superuser = True
            user.is_staff = True
        user.save()

        if as_collector:
            try:
                group = Group.objects.get(name=settings.COLLECTORS_GROUP_NAME)
                user.groups.add(group)
            except Group.DoesNotExist:
                self.stderr.write(
                    f"Warning: {settings.COLLECTORS_GROUP_NAME!r} group not found. Run migrations first."
                )

        roles = []
        if as_admin:
            roles.append("admin")
        if as_collector:
            roles.append("collector")
        role_str = f" ({', '.join(roles)})" if roles else ""
        self.stdout.write(f"Created user {username!r}{role_str}")
