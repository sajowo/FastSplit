# Generated by Django 5.0.6 on 2024-06-19 17:02

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('EsSplit', '0008_alter_friend_name_alter_friend_user'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Bill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('description', models.TextField()),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_bills', to=settings.AUTH_USER_MODEL)),
                ('participants', models.ManyToManyField(related_name='participated_bills', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]