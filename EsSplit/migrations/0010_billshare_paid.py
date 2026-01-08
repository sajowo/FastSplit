from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('EsSplit', '0009_billshare_rejected'),
    ]

    operations = [
        migrations.AddField(
            model_name='billshare',
            name='paid',
            field=models.BooleanField(default=False),
        ),
    ]
