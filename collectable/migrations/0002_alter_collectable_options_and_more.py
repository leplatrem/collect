# Generated by Django 5.1 on 2024-08-23 08:34

import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("collectable", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="collectable",
            options={
                "verbose_name": "Collectable",
                "verbose_name_plural": "Collectables",
            },
        ),
        migrations.AlterModelOptions(
            name="historicalcollectable",
            options={
                "get_latest_by": ("history_date", "history_id"),
                "ordering": ("-history_date", "-history_id"),
                "verbose_name": "History",
                "verbose_name_plural": "historical Collectables",
            },
        ),
        migrations.AlterModelOptions(
            name="possession",
            options={
                "verbose_name": "Possession",
                "verbose_name_plural": "Possessions",
            },
        ),
        migrations.AlterField(
            model_name="collectable",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
        ),
        migrations.AlterField(
            model_name="collectable",
            name="id",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                primary_key=True,
                serialize=False,
                verbose_name="Identifier",
            ),
        ),
        migrations.AlterField(
            model_name="collectable",
            name="modified_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Modified at"),
        ),
        migrations.AlterField(
            model_name="collectable",
            name="photo",
            field=models.ImageField(upload_to="collectables/%Y/", verbose_name="Photo"),
        ),
        migrations.AlterField(
            model_name="historicalcollectable",
            name="created_at",
            field=models.DateTimeField(
                blank=True, editable=False, verbose_name="Created at"
            ),
        ),
        migrations.AlterField(
            model_name="historicalcollectable",
            name="id",
            field=models.UUIDField(
                db_index=True,
                default=uuid.uuid4,
                editable=False,
                verbose_name="Identifier",
            ),
        ),
        migrations.AlterField(
            model_name="historicalcollectable",
            name="photo",
            field=models.TextField(max_length=100, verbose_name="Photo"),
        ),
        migrations.AlterField(
            model_name="possession",
            name="likes",
            field=models.BooleanField(default=False, verbose_name="Likes"),
        ),
        migrations.AlterField(
            model_name="possession",
            name="owns",
            field=models.BooleanField(default=True, verbose_name="Owns"),
        ),
        migrations.AlterField(
            model_name="possession",
            name="wants",
            field=models.BooleanField(default=False, verbose_name="Wants"),
        ),
        migrations.AlterUniqueTogether(
            name="possession",
            unique_together={("user", "collectable")},
        ),
    ]