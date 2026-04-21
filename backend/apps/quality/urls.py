from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('brands', views.BrandViewSet)
router.register('moisture-data', views.MoistureDataViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('knowledge/search/', views.search_knowledge, name='quality-knowledge-search'),
    path('analysis/summary/', views.moisture_analysis_summary, name='quality-analysis-summary'),
    path('analysis/anomalies/', views.moisture_anomaly_alerts, name='quality-anomaly-alerts'),
    path('analysis/daily-report/', views.moisture_daily_report, name='quality-daily-report'),
]
