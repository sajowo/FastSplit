# Generated by Django 5.0.6 on 2024-06-19 17:16

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('EsSplit', '0009_bill'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bill',
            name='date',
        ),
        migrations.AlterField(
            model_name='bill',
            name='amount',
            field=models.FloatField(),
        ),
        migrations.AlterField(
            model_name='bill',
            name='description',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='bill',
            name='participants',
            field=models.ManyToManyField(related_name='bills', to=settings.AUTH_USER_MODEL),
        ),
    ]
