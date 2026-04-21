from django.contrib import admin
from .models import Location, HazardReport, HazardImage


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
