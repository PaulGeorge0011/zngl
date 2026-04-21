from django.contrib import admin
from .models import Equipment, MonitorPoint


class MonitorPointInline(admin.TabularInline):
    model = MonitorPoint
    extra = 1


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'location', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['name', 'code', 'location']
    inlines = [MonitorPointInline]


@admin.register(MonitorPoint)
class MonitorPointAdmin(admin.ModelAdmin):
    list_display = ['name', 'equipment', 'param_type', 'unit']
    list_filter = ['param_type']
