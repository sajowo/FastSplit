from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('EsSplit', '0007_rename_essplit_log_ip_77a2f8_idx_essplit_log_ip_addr_9e5313_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='billshare',
            name='accepted',
            field=models.BooleanField(default=False),
        ),
    ]
