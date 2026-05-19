from django.apps import apps as real_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations

from collect import settings


def create_collectors_group(apps, schema_editor):
    # Create permissions for collectable app to ensure they exist before assigning them to the group.
    create_permissions(real_apps.get_app_config("collectable"), verbosity=0)

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    group, _ = Group.objects.get_or_create(name=settings.COLLECTORS_GROUP_NAME)
    perms = Permission.objects.filter(
        content_type__app_label="collectable",
        content_type__model="collectable",
        codename__in=["add_collectable", "change_collectable", "delete_collectable"],
    )
    group.permissions.add(*perms)
    perms = Permission.objects.filter(
        content_type__app_label="collectable",
        content_type__model="duplicatereport",
        codename__in=["add_duplicatereport", "delete_duplicatereport"],
    )
    group.permissions.add(*perms)


class Migration(migrations.Migration):
    dependencies = [
        ("collectable", "0009_collectable_license_historicalcollectable_license"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_collectors_group),
    ]
