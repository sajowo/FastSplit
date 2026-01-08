from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('EsSplit', '0008_billshare_accepted'),
    ]

    operations = [
        migrations.AddField(
            model_name='billshare',
            name='rejected',
            field=models.BooleanField(default=False),
        ),
    ]
