from django.db import models


class Brand(models.Model):
    """牌号"""

    name = models.CharField(max_length=100, unique=True, verbose_name='牌号名称')
    target_moisture = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=12.40,
        verbose_name='目标成品水分',
    )
    moisture_tolerance = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.50,
        verbose_name='成品水分容差',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'quality_brand'
        ordering = ['name']

    def __str__(self):
        return self.name


class MoistureData(models.Model):
    """成品水分数据"""

    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='moisture_data')

    sampling_date = models.DateField(null=True, blank=True, verbose_name='取样日期')
    sample_number = models.CharField(max_length=100, verbose_name='样品编号')
    machine_number = models.CharField(max_length=50, verbose_name='机台号')
    machine_stage = models.CharField(max_length=50, verbose_name='机台')

    finished_moisture = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='成品水分')
    powder_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='含末率')
    addition_method = models.CharField(max_length=100, null=True, blank=True, verbose_name='加丝方式/加丝机')
    batch_number = models.CharField(max_length=100, null=True, blank=True, verbose_name='批次号')
    shift = models.CharField(max_length=50, null=True, blank=True, verbose_name='班次')
    drying_moisture = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='烘丝水分')
    mixed_moisture = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='混合丝水分')
    cabinet_moisture = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='出柜水分')
    rolling_moisture = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='卷制水分')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quality_moisture_data'
        ordering = ['-sampling_date', '-created_at']

    def __str__(self):
        return f'{self.brand.name} - {self.sample_number}'
