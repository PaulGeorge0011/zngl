from rest_framework import serializers
from .models import ThresholdRule, SensorReading, AlarmRecord, RepairAdvice


class ThresholdRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThresholdRule
        fields = ['id', 'monitor_point', 'warning_high', 'warning_low',
                  'alarm_high', 'alarm_low', 'is_active']


class SensorReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorReading
        fields = ['id', 'monitor_point', 'value', 'recorded_at']


class SensorReadingBatchSerializer(serializers.Serializer):
    """批量接收传感器数据"""
    readings = SensorReadingSerializer(many=True)


class AlarmRecordSerializer(serializers.ModelSerializer):
    equipment_name = serializers.CharField(source='monitor_point.equipment.name', read_only=True)
    equipment_id = serializers.IntegerField(source='monitor_point.equipment.id', read_only=True)
    point_name = serializers.CharField(source='monitor_point.name', read_only=True)
    param_type = serializers.CharField(source='monitor_point.param_type', read_only=True)
    unit = serializers.CharField(source='monitor_point.unit', read_only=True)
    has_repair_advice = serializers.SerializerMethodField()

    class Meta:
        model = AlarmRecord
        fields = [
            'id', 'monitor_point', 'equipment_name', 'equipment_id',
            'point_name', 'param_type', 'unit',
            'level', 'status', 'triggered_value', 'threshold_value',
            'triggered_at', 'resolved_at', 'note', 'has_repair_advice',
        ]

    def get_has_repair_advice(self, obj):
        return hasattr(obj, 'repair_advice')


class RepairAdviceSerializer(serializers.ModelSerializer):
    alarm_info = AlarmRecordSerializer(source='alarm', read_only=True)

    class Meta:
        model = RepairAdvice
        fields = ['id', 'alarm', 'alarm_info', 'ai_response', 'ragflow_context', 'created_at']
