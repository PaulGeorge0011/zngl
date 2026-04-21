from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('brands', views.BrandViewSet)
router.register('moisture-data', views.MoistureDataViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('knowledge/search/', views.search_knowledge, name='quality-knowledge-search'),
]
