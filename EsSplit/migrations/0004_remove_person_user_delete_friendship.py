# Generated by Django 5.0.6 on 2024-06-18 14:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('EsSplit', '0003_person_user_friendship'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='person',
            name='user',
        ),
        migrations.DeleteModel(
            name='Friendship',
        ),
    ]