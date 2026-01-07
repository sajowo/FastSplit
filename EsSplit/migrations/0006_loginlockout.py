from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('EsSplit', '0005_alter_group_creator_billshare'),
    ]

    operations = [
        migrations.CreateModel(
            name='LoginLockout',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.CharField(max_length=64)),
                ('email', models.CharField(max_length=254)),
                ('failures', models.PositiveIntegerField(default=0)),
                ('lockout_level', models.PositiveIntegerField(default=0)),
                ('locked_until', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'unique_together': {('ip_address', 'email')},
            },
        ),
        migrations.AddIndex(
            model_name='loginlockout',
            index=models.Index(fields=['ip_address', 'email'], name='EsSplit_log_ip_77a2f8_idx'),
        ),
        migrations.AddIndex(
            model_name='loginlockout',
            index=models.Index(fields=['locked_until'], name='EsSplit_log_lo_4d1f0e_idx'),
        ),
    ]
