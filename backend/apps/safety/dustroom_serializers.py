from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (
    DustRoom, InspectionTemplate, InspectionItem,
    DustRoomInspector, InspectionRecord, InspectionItemResult,
    INSPECTION_ROLE_CHOICES,
)


class DustRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = DustRoom
        fields = ['id', 'name', 'code', 'description', 'is_active', 'sort_order']


class InspectionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspectionItem
        fields = ['id', 'template', 'name', 'item_type', 'options', 'unit', 'required', 'sort_order']
        read_only_fields = ['template']


class InspectionTemplateSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    items = InspectionItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(source='items.count', read_only=True)

    class Meta:
        model = InspectionTemplate
        fields = ['id', 'role', 'role_display', 'name', 'frequency', 'is_active', 'items', 'items_count']


class InspectionTemplateListSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    items_count = serializers.IntegerField(source='items.count', read_only=True)

    class Meta:
        model = InspectionTemplate
        fields = ['id', 'role', 'role_display', 'name', 'frequency', 'is_active', 'items_count']


class UserBriefSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'display_name']

    def get_display_name(self, obj):
        return obj.get_full_name() or obj.username


class DustRoomInspectorSerializer(serializers.ModelSerializer):
    user_display = UserBriefSerializer(source='user', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = DustRoomInspector
        fields = ['id', 'user', 'role', 'user_display', 'role_display']


class InspectionItemResultSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_type = serializers.CharField(source='item.item_type', read_only=True)
    item_unit = serializers.CharField(source='item.unit', read_only=True)

    class Meta:
        model = InspectionItemResult
        fields = ['id', 'item', 'item_name', 'item_type', 'item_unit', 'value', 'is_normal', 'remark']


class InspectionRecordListSerializer(serializers.ModelSerializer):
    dust_room_name = serializers.CharField(source='dust_room.name', read_only=True)
    role_display = serializers.CharField(source='template.get_role_display', read_only=True)
    inspector_display = UserBriefSerializer(source='inspector', read_only=True)
    abnormal_count = serializers.SerializerMethodField()

    class Meta:
        model = InspectionRecord
        fields = [
            'id', 'dust_room', 'dust_room_name', 'template',
            'role_display', 'inspector_display',
            'inspection_date', 'status', 'has_abnormal',
            'abnormal_count', 'created_at', 'submitted_at',
        ]

    def get_abnormal_count(self, obj):
        return obj.results.filter(is_normal=False).count()


class InspectionRecordDetailSerializer(serializers.ModelSerializer):
    dust_room_name = serializers.CharField(source='dust_room.name', read_only=True)
    role_display = serializers.CharField(source='template.get_role_display', read_only=True)
    inspector_display = UserBriefSerializer(source='inspector', read_only=True)
    results = InspectionItemResultSerializer(many=True, read_only=True)

    class Meta:
        model = InspectionRecord
        fields = [
            'id', 'dust_room', 'dust_room_name', 'template',
            'role_display', 'inspector_display',
            'inspection_date', 'status', 'has_abnormal', 'remark',
            'results', 'created_at', 'submitted_at',
        ]
