from django.db import models


class Equipment(models.Model):
    """设备基础信息"""

    STATUS_CHOICES = [
        ('running', '运行中'),
        ('stopped', '停机'),
        ('fault', '故障'),
    ]

    name = models.CharField('设备名称', max_length=100)
    code = models.CharField('设备编号', max_length=50, unique=True)
    location = models.CharField('安装地点', max_length=200)
    description = models.TextField('描述', blank=True, default='')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='stopped')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '设备'
        verbose_name_plural = '设备'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name}({self.code})"


class MonitorPoint(models.Model):
    """监控参数定义"""

    PARAM_TYPE_CHOICES = [
        ('temperature', '温度'),
        ('current', '电流'),
        ('vibration', '振动'),
    ]

    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, related_name='monitor_points', verbose_name='所属设备'
    )
    name = models.CharField('监控点名称', max_length=50)
    param_key = models.CharField('参数标识', max_length=50)
    unit = models.CharField('单位', max_length=20)
    param_type = models.CharField('参数类型', max_length=20, choices=PARAM_TYPE_CHOICES)

    class Meta:
        verbose_name = '监控点'
        verbose_name_plural = '监控点'
        unique_together = ['equipment', 'param_key']

    def __str__(self):
        return f"{self.equipment.name} - {self.name}"


class CollectionInterface(models.Model):
    INTERFACE_TYPES = [('http', 'HTTP'), ('mqtt', 'MQTT')]

    monitor_point = models.OneToOneField(
        MonitorPoint, on_delete=models.CASCADE, related_name='collection'
    )
    interface_type = models.CharField('接口类型', max_length=10, choices=INTERFACE_TYPES)
    config = models.JSONField('配置参数', default=dict)
    polling_interval = models.IntegerField('轮询间隔(秒)', default=60)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '采集接口'
        verbose_name_plural = '采集接口'

    def __str__(self):
        return f"{self.monitor_point.name} - {self.interface_type}"
