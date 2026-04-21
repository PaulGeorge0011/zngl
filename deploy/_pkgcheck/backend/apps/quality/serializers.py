from rest_framework import serializers
from .models import Brand, MoistureData


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'created_at']


class MoistureDataSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source='brand.name', read_only=True)

    # 自动计算字段
    drying_mixed_diff = serializers.SerializerMethodField()
    mixed_cabinet_diff = serializers.SerializerMethodField()
    cabinet_rolling_diff = serializers.SerializerMethodField()
    rolling_finished_diff = serializers.SerializerMethodField()
    mixed_finished_diff = serializers.SerializerMethodField()

    class Meta:
        model = MoistureData
        fields = [
            'id', 'brand', 'brand_name', 'sampling_date', 'sample_number',
            'machine_number', 'machine_stage', 'finished_moisture', 'powder_rate',
            'addition_method', 'batch_number', 'shift', 'drying_moisture',
            'mixed_moisture', 'cabinet_moisture', 'rolling_moisture',
            'drying_mixed_diff', 'mixed_cabinet_diff', 'cabinet_rolling_diff',
            'rolling_finished_diff', 'mixed_finished_diff', 'created_at', 'updated_at'
        ]

    def get_drying_mixed_diff(self, obj):
        if obj.drying_moisture and obj.mixed_moisture:
            return round(float(obj.drying_moisture - obj.mixed_moisture), 2)
        return None

    def get_mixed_cabinet_diff(self, obj):
        if obj.mixed_moisture and obj.cabinet_moisture:
            return round(float(obj.mixed_moisture - obj.cabinet_moisture), 2)
        return None

    def get_cabinet_rolling_diff(self, obj):
        if obj.cabinet_moisture and obj.rolling_moisture:
            return round(float(obj.cabinet_moisture - obj.rolling_moisture), 2)
        return None

    def get_rolling_finished_diff(self, obj):
        if obj.rolling_moisture and obj.finished_moisture:
            return round(float(obj.rolling_moisture - obj.finished_moisture), 2)
        return None

    def get_mixed_finished_diff(self, obj):
        if obj.mixed_moisture and obj.finished_moisture:
            return round(float(obj.mixed_moisture - obj.finished_moisture), 2)
        return None
