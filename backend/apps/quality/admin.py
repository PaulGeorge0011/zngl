from django.contrib import admin
from .models import Brand, MoistureData


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(MoistureData)
class MoistureDataAdmin(admin.ModelAdmin):
    list_display = ['brand', 'sampling_date', 'sample_number', 'finished_moisture']
    list_filter = ['brand', 'sampling_date']
    search_fields = ['sample_number', 'batch_number']
