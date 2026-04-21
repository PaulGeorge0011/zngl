from django.urls import path
from . import views

urlpatterns = [
    path('repair-advice/', views.generate_repair_advice, name='generate-repair-advice'),
    path('repair-advice/<int:alarm_id>/', views.get_repair_advice, name='get-repair-advice'),
    path('quality-assistant/', views.quality_analysis_assistant, name='quality-analysis-assistant'),
]
