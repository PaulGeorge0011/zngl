from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (
    NightShiftCategory, NightShiftCheckItem, NightShiftDuty,
    NightShiftRecord, NightShiftCheckResult, NightShiftIssue,
)


class NightShiftCheckItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NightShiftCheckItem
        fields = ['id', 'category', 'name', 'is_active', 'sort_order']
        read_only_fields = ['category']


class NightShiftCategorySerializer(serializers.ModelSerializer):
    items = NightShiftCheckItemSerializer(many=True, read_only=True)
    items_count = serializers.IntegerField(source='items.count', read_only=True)

    class Meta:
        model = NightShiftCategory
        fields = ['id', 'name', 'allows_custom', 'sort_order', 'is_active', 'items', 'items_count']


class NightShiftCategoryListSerializer(serializers.ModelSerializer):
    items_count = serializers.IntegerField(source='items.count', read_only=True)

    class Meta:
        model = NightShiftCategory
        fields = ['id', 'name', 'allows_custom', 'sort_order', 'is_active', 'items_count']


class UserBriefSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'display_name']

    def get_display_name(self, obj):
        return obj.get_full_name() or obj.username


class NightShiftCheckResultSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    item_name = serializers.SerializerMethodField()

    class Meta:
        model = NightShiftCheckResult
        fields = ['id', 'category', 'category_name', 'item', 'item_name',
                  'custom_name', 'is_normal', 'remark']

    def get_item_name(self, obj):
        if obj.item:
            return obj.item.name
        return obj.custom_name


class NightShiftIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = NightShiftIssue
        fields = ['id', 'description', 'rectification', 'is_resolved']


class NightShiftRecordListSerializer(serializers.ModelSerializer):
    inspector_display = UserBriefSerializer(source='inspector', read_only=True)
    abnormal_count = serializers.SerializerMethodField()
    issue_count = serializers.SerializerMethodField()
    unresolved_count = serializers.SerializerMethodField()

    class Meta:
        model = NightShiftRecord
        fields = ['id', 'inspector_display', 'inspection_date', 'status',
                  'has_issues', 'abnormal_count', 'issue_count',
                  'unresolved_count', 'created_at', 'submitted_at']

    def get_abnormal_count(self, obj):
        return obj.results.filter(is_normal=False).count()

    def get_issue_count(self, obj):
        return obj.issues.count()

    def get_unresolved_count(self, obj):
        return obj.issues.filter(is_resolved=False).count()


class NightShiftRecordDetailSerializer(serializers.ModelSerializer):
    inspector_display = UserBriefSerializer(source='inspector', read_only=True)
    results = NightShiftCheckResultSerializer(many=True, read_only=True)
    issues = NightShiftIssueSerializer(many=True, read_only=True)
    duty_id = serializers.IntegerField(source='duty.id', read_only=True, default=None)

    class Meta:
        model = NightShiftRecord
        fields = ['id', 'duty_id', 'inspector_display', 'inspection_date', 'status',
                  'has_issues', 'overall_remark', 'results', 'issues',
                  'created_at', 'submitted_at']


class NightShiftDutySerializer(serializers.ModelSerializer):
    inspector_display = UserBriefSerializer(source='inspector', read_only=True)
    inspector_phone = serializers.SerializerMethodField()
    created_by_display = UserBriefSerializer(source='created_by', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    record_id = serializers.IntegerField(source='record.id', read_only=True, default=None)
    has_issues = serializers.SerializerMethodField()

    class Meta:
        model = NightShiftDuty
        fields = ['id', 'duty_date', 'inspector', 'inspector_display', 'inspector_phone',
                  'status', 'status_display', 'record_id', 'has_issues',
                  'sms_sent_at',
                  'created_by', 'created_by_display', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'status', 'record',
                            'sms_sent_at']

    def get_has_issues(self, obj):
        if obj.record:
            return obj.record.has_issues
        return False

    def get_inspector_phone(self, obj):
        user = obj.inspector
        if not user:
            return ''
        profile = getattr(user, 'profile', None)
        if profile and getattr(profile, 'phone', ''):
            return profile.phone
        return ''
