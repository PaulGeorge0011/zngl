from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quality', '0004_alter_moisturedata_rolling_moisture'),
    ]

    operations = [
        migrations.AddField(
            model_name='brand',
            name='moisture_tolerance',
            field=models.DecimalField(decimal_places=2, default=0.5, max_digits=4, verbose_name='成品水分容差'),
        ),
        migrations.AddField(
            model_name='brand',
            name='target_moisture',
            field=models.DecimalField(decimal_places=2, default=12.4, max_digits=4, verbose_name='目标成品水分'),
        ),
    ]
