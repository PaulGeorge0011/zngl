from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EquipmentViewSet, MonitorPointViewSet

router = DefaultRouter()
router.register('equipments', EquipmentViewSet)
router.register('monitor-points', MonitorPointViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
