from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('safety', '0006_nightshiftduty_nightshiftrecord_duty'),
    ]

    operations = [
        migrations.AddField(
            model_name='nightshiftduty',
            name='sms_sent_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='短信通知时间'),
        ),
    ]
