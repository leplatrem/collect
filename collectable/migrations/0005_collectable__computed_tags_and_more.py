# Generated by Django 5.1 on 2024-09-13 07:57

from django.db import migrations, models


def forwards_func(apps, schema_editor):
    from django.contrib.auth import get_user_model

    from collectable.models import Collectable

    User = get_user_model()

    admin = User.objects.first()

    for item in Collectable.objects.all():
        item._history_user = admin
        # Fill `_computed_tags` field.
        item.save()


def reverse_func(apps, schema_editor):
    # Nothing to do.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("collectable", "0004_alter_collectable_description_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="collectable",
            name="_computed_tags",
            field=models.TextField(verbose_name="Tags"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="historicalcollectable",
            name="_computed_tags",
            field=models.TextField(verbose_name="Tags"),
            preserve_default=False,
        ),
        migrations.RunPython(forwards_func, reverse_func),
    ]
