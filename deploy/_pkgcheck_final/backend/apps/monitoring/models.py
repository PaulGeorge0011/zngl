from django.db import models


class ThresholdRule(models.Model):
    """阈值规则：每个监控点可配置预警/报警上下限"""

    monitor_point = models.OneToOneField(
        'equipment.MonitorPoint', on_delete=models.CASCADE,
        related_name='threshold', verbose_name='监控点'
    )
    warning_high = models.FloatField('预警上限', null=True, blank=True)
    warning_low = models.FloatField('预警下限', null=True, blank=True)
    alarm_high = models.FloatField('报警上限', null=True, blank=True)
    alarm_low = models.FloatField('报警下限', null=True, blank=True)
    is_active = models.BooleanField('启用', default=True)

    class Meta:
        verbose_name = '阈值规则'
        verbose_name_plural = '阈值规则'

    def __str__(self):
        return f"{self.monitor_point} 阈值"


class SensorReading(models.Model):
    """传感器数据记录（时序数据）"""

    monitor_point = models.ForeignKey(
        'equipment.MonitorPoint', on_delete=models.CASCADE,
        related_name='readings', verbose_name='监控点'
    )
    value = models.FloatField('采集值')
    recorded_at = models.DateTimeField('采集时间', db_index=True)

    class Meta:
        verbose_name = '传感器数据'
        verbose_name_plural = '传感器数据'
        ordering = ['-recorded_at']


class AlarmRecord(models.Model):
    """报警记录"""

    LEVEL_CHOICES = [
        ('warning', '预警'),
        ('alarm', '报警'),
    ]
    STATUS_CHOICES = [
        ('active', '未处理'),
        ('acknowledged', '已确认'),
        ('resolved', '已解决'),
    ]

    monitor_point = models.ForeignKey(
        'equipment.MonitorPoint', on_delete=models.CASCADE,
        related_name='alarms', verbose_name='监控点'
    )
    level = models.CharField('级别', max_length=20, choices=LEVEL_CHOICES)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='active')
    triggered_value = models.FloatField('触发值')
    threshold_value = models.FloatField('阈值')
    triggered_at = models.DateTimeField('触发时间', auto_now_add=True)
    resolved_at = models.DateTimeField('解决时间', null=True, blank=True)
    note = models.TextField('处理备注', blank=True, default='')

    class Meta:
        verbose_name = '报警记录'
        verbose_name_plural = '报警记录'
        ordering = ['-triggered_at']

    def __str__(self):
        return f"{self.monitor_point} - {self.get_level_display()} - {self.get_status_display()}"


class RepairAdvice(models.Model):
    """AI 维修建议"""

    alarm = models.OneToOneField(
        AlarmRecord, on_delete=models.CASCADE, related_name='repair_advice', verbose_name='报警记录'
    )
    ai_response = models.TextField('AI回复')
    ragflow_context = models.TextField('知识库上下文', blank=True, default='')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '维修建议'
        verbose_name_plural = '维修建议'
