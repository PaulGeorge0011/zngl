from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('thresholds', views.ThresholdRuleViewSet)
router.register('alarms', views.AlarmRecordViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('readings/', views.receive_readings, name='receive-readings'),
    path('readings/history/', views.get_readings_history, name='readings-history'),
    path('latest/', views.get_latest_readings, name='latest-readings'),
    path('dashboard/', views.dashboard_stats, name='dashboard-stats'),
]
