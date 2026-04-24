"""整改工单相关序列化器。"""
from rest_framework import serializers

from .models import RectificationOrder, RectificationImage, RectificationLog
from .serializers import UserBriefSerializer


class RectificationImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = RectificationImage
        fields = ['id', 'image_url', 'phase', 'created_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None


class RectificationLogSerializer(serializers.ModelSerializer):
    operator = UserBriefSerializer(read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = RectificationLog
        fields = [
            'id', 'action', 'action_display',
            'operator', 'from_status', 'to_status',
            'remark', 'created_at',
        ]


class RectificationListSerializer(serializers.ModelSerializer):
    submitter = UserBriefSerializer(read_only=True)
    assignee = UserBriefSerializer(read_only=True)
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)

    class Meta:
        model = RectificationOrder
        fields = [
            'id',
            'source_type', 'source_type_display', 'source_id',
            'title', 'location_text',
            'severity', 'severity_display',
            'status', 'status_display',
            'submitter', 'assignee',
            'assigned_at', 'deadline', 'rectified_at',
            'overdue', 'reject_count',
            'created_at', 'updated_at',
        ]


class RectificationDetailSerializer(serializers.ModelSerializer):
    submitter = UserBriefSerializer(read_only=True)
    assignee = UserBriefSerializer(read_only=True)
    assigner = UserBriefSerializer(read_only=True)
    verifier = UserBriefSerializer(read_only=True)
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    images = RectificationImageSerializer(many=True, read_only=True)
    logs = RectificationLogSerializer(many=True, read_only=True)

    class Meta:
        model = RectificationOrder
        fields = [
            'id',
            'source_type', 'source_type_display', 'source_id', 'source_snapshot',
            'title', 'description', 'location_text',
            'severity', 'severity_display',
            'status', 'status_display',
            'submitter', 'assignee', 'assigner',
            'assigned_at', 'deadline',
            'rectify_description', 'rectified_at',
            'verifier', 'verified_at', 'verify_remark',
            'reject_count', 'overdue',
            'created_at', 'updated_at',
            'images', 'logs',
        ]
