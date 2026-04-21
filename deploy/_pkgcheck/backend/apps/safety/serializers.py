from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Location, HazardReport, HazardImage


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'sort_order']


class HazardImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = HazardImage
        fields = ['id', 'image_url', 'phase', 'created_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None


class UserBriefSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'display_name']

    def get_display_name(self, obj):
        return obj.get_full_name() or obj.username


class HazardListSerializer(serializers.ModelSerializer):
    reporter = UserBriefSerializer(read_only=True)
    assignee = UserBriefSerializer(read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = HazardReport
        fields = [
            'id', 'title', 'level', 'level_display',
            'location', 'location_name', 'location_detail',
            'status', 'status_display',
            'reporter', 'assignee', 'created_at',
        ]


class HazardDetailSerializer(serializers.ModelSerializer):
    reporter = UserBriefSerializer(read_only=True)
    assignee = UserBriefSerializer(read_only=True)
    assigned_by = UserBriefSerializer(read_only=True)
    verified_by = UserBriefSerializer(read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    images = HazardImageSerializer(many=True, read_only=True)

    class Meta:
        model = HazardReport
        fields = [
            'id', 'title', 'description',
            'level', 'level_display',
            'location', 'location_name', 'location_detail',
            'status', 'status_display',
            'reporter', 'assignee', 'assigned_by', 'assigned_at',
            'fix_description', 'fixed_at',
            'verified_by', 'verified_at', 'verify_remark',
            'created_at', 'updated_at',
            'images',
        ]


class HazardCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HazardReport
        fields = ['title', 'description', 'level', 'location', 'location_detail']

    def validate_level(self, value):
        if value not in ('general', 'major'):
            raise serializers.ValidationError('等级无效')
        return value
