from django.contrib import admin
from .models import ThresholdRule, SensorReading, AlarmRecord, RepairAdvice


@admin.register(ThresholdRule)
class ThresholdRuleAdmin(admin.ModelAdmin):
    list_display = ['monitor_point', 'warning_high', 'warning_low', 'alarm_high', 'alarm_low', 'is_active']


@admin.register(AlarmRecord)
class AlarmRecordAdmin(admin.ModelAdmin):
    list_display = ['monitor_point', 'level', 'status', 'triggered_value', 'threshold_value', 'triggered_at']
    list_filter = ['level', 'status']


@admin.register(RepairAdvice)
class RepairAdviceAdmin(admin.ModelAdmin):
    list_display = ['alarm', 'created_at']
