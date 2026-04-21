from django.contrib import admin
from .models import (
    Location, HazardReport, HazardImage,
    DustRoom, InspectionTemplate, InspectionItem,
    DustRoomInspector, InspectionRecord, InspectionItemResult,
    NightShiftCategory, NightShiftCheckItem, NightShiftDuty,
    NightShiftRecord, NightShiftCheckResult, NightShiftIssue,
)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'sort_order', 'is_active']
    list_editable = ['sort_order', 'is_active']
    ordering = ['sort_order', 'name']


class HazardImageInline(admin.TabularInline):
    model = HazardImage
    extra = 0
    readonly_fields = ['phase', 'created_at']


@admin.register(HazardReport)
class HazardReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'level', 'location', 'status', 'reporter', 'created_at']
    list_filter = ['status', 'level', 'location']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [HazardImageInline]


# ── 除尘房巡检 ─────────────────────────────────────────────────

@admin.register(DustRoom)
class DustRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'sort_order']
    list_editable = ['sort_order', 'is_active']
    ordering = ['sort_order']


class InspectionItemInline(admin.TabularInline):
    model = InspectionItem
    extra = 1
    ordering = ['sort_order']


@admin.register(InspectionTemplate)
class InspectionTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'role', 'frequency', 'is_active']
    list_filter = ['role', 'is_active']
    inlines = [InspectionItemInline]


@admin.register(DustRoomInspector)
class DustRoomInspectorAdmin(admin.ModelAdmin):
    list_display = ['user', 'role']
    list_filter = ['role']


class InspectionItemResultInline(admin.TabularInline):
    model = InspectionItemResult
    extra = 0
    readonly_fields = ['item', 'value', 'is_normal', 'remark']


@admin.register(InspectionRecord)
class InspectionRecordAdmin(admin.ModelAdmin):
    list_display = ['dust_room', 'template', 'inspector', 'inspection_date', 'status', 'has_abnormal']
    list_filter = ['status', 'has_abnormal', 'dust_room', 'inspection_date']
    readonly_fields = ['created_at', 'submitted_at']
    inlines = [InspectionItemResultInline]


# ── 夜班监护检查 ───────────────────────────────────────────────

class NightShiftCheckItemInline(admin.TabularInline):
    model = NightShiftCheckItem
    extra = 1
    ordering = ['sort_order']


@admin.register(NightShiftCategory)
class NightShiftCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'allows_custom', 'sort_order', 'is_active']
    list_editable = ['sort_order', 'is_active']
    inlines = [NightShiftCheckItemInline]


@admin.register(NightShiftDuty)
class NightShiftDutyAdmin(admin.ModelAdmin):
    list_display = ['duty_date', 'inspector', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'duty_date']
    readonly_fields = ['created_at', 'updated_at']


class NightShiftCheckResultInline(admin.TabularInline):
    model = NightShiftCheckResult
    extra = 0
    readonly_fields = ['category', 'item', 'custom_name', 'is_normal', 'remark']


class NightShiftIssueInline(admin.TabularInline):
    model = NightShiftIssue
    extra = 0


@admin.register(NightShiftRecord)
class NightShiftRecordAdmin(admin.ModelAdmin):
    list_display = ['inspector', 'inspection_date', 'status', 'has_issues']
    list_filter = ['status', 'has_issues', 'inspection_date']
    readonly_fields = ['created_at', 'submitted_at']
    inlines = [NightShiftCheckResultInline, NightShiftIssueInline]
