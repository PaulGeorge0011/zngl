from rest_framework import serializers
from django.db import transaction
from .models import Equipment, MonitorPoint, CollectionInterface
from apps.monitoring.models import ThresholdRule


class ThresholdRuleInlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThresholdRule
        fields = ['id', 'warning_high', 'warning_low', 'alarm_high', 'alarm_low', 'is_active']


class CollectionInterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionInterface
        fields = ['id', 'interface_type', 'config', 'polling_interval', 'is_active', 'updated_at']

    def validate(self, data):
        itype = data.get('interface_type', getattr(self.instance, 'interface_type', None))
        config = data.get('config', getattr(self.instance, 'config', {}))
        if itype == 'http' and not config.get('url'):
            raise serializers.ValidationError({'config': 'HTTP 接口必须填写 url'})
        if itype == 'mqtt' and (not config.get('broker') or not config.get('topic')):
            raise serializers.ValidationError({'config': 'MQTT 接口必须填写 broker 和 topic'})
        return data


class MonitorPointSerializer(serializers.ModelSerializer):
    threshold = ThresholdRuleInlineSerializer(read_only=True)
    collection = CollectionInterfaceSerializer(read_only=True)

    class Meta:
        model = MonitorPoint
        fields = ['id', 'equipment', 'name', 'param_key', 'unit', 'param_type', 'threshold', 'collection']


class MonitorPointCreateSerializer(serializers.ModelSerializer):
    warning_high = serializers.FloatField(write_only=True, required=False, allow_null=True)
    warning_low = serializers.FloatField(write_only=True, required=False, allow_null=True)
    alarm_high = serializers.FloatField(write_only=True, required=False, allow_null=True)
    alarm_low = serializers.FloatField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = MonitorPoint
        fields = [
            'id', 'equipment', 'name', 'param_key', 'unit', 'param_type',
            'warning_high', 'warning_low', 'alarm_high', 'alarm_low',
        ]

    def create(self, validated_data):
        threshold_data = {
            'warning_high': validated_data.pop('warning_high', None),
            'warning_low': validated_data.pop('warning_low', None),
            'alarm_high': validated_data.pop('alarm_high', None),
            'alarm_low': validated_data.pop('alarm_low', None),
        }
        with transaction.atomic():
            point = MonitorPoint.objects.create(**validated_data)
            ThresholdRule.objects.create(monitor_point=point, **threshold_data)
        return point

    def update(self, instance, validated_data):
        threshold_data = {
            'warning_high': validated_data.pop('warning_high', None),
            'warning_low': validated_data.pop('warning_low', None),
            'alarm_high': validated_data.pop('alarm_high', None),
            'alarm_low': validated_data.pop('alarm_low', None),
        }
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        ThresholdRule.objects.update_or_create(
            monitor_point=instance, defaults=threshold_data
        )
        return instance


class EquipmentListSerializer(serializers.ModelSerializer):
    monitor_points_count = serializers.IntegerField(source='monitor_points.count', read_only=True)
    active_alarms_count = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = [
            'id', 'name', 'code', 'location', 'description', 'status',
            'monitor_points_count', 'active_alarms_count', 'created_at', 'updated_at',
        ]

    def get_active_alarms_count(self, obj):
        from apps.monitoring.models import AlarmRecord
        return AlarmRecord.objects.filter(
            monitor_point__equipment=obj, status='active'
        ).count()


class EquipmentDetailSerializer(serializers.ModelSerializer):
    monitor_points = MonitorPointSerializer(many=True, read_only=True)

    class Meta:
        model = Equipment
        fields = [
            'id', 'name', 'code', 'location', 'description', 'status',
            'monitor_points', 'created_at', 'updated_at',
        ]
