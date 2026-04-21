from django.urls import path
from . import views

urlpatterns = [
    # Knowledge base (existing)
    path('knowledge/search/', views.search_knowledge, name='safety-knowledge-search'),

    # Locations
    path('locations/', views.location_list, name='safety-location-list'),

    # Hazard reports
    path('hazards/', views.hazard_list_create, name='safety-hazard-list'),
    path('hazards/<int:pk>/', views.hazard_detail, name='safety-hazard-detail'),
    path('hazards/<int:pk>/assign/', views.hazard_assign, name='safety-hazard-assign'),
    path('hazards/<int:pk>/fix/', views.hazard_fix, name='safety-hazard-fix'),
    path('hazards/<int:pk>/verify/', views.hazard_verify, name='safety-hazard-verify'),

    # 夹层施工管理
    path('mezzanine/checkin/', views.mezzanine_checkin, name='mezzanine-checkin'),
    path('mezzanine/onsite/', views.mezzanine_onsite, name='mezzanine-onsite'),
    path('mezzanine/checkout/', views.mezzanine_checkout, name='mezzanine-checkout'),
    path('mezzanine/history/', views.mezzanine_history, name='mezzanine-history'),

    # 夹层施工管理 CRUD
    path('mezzanine/manage/', views.mezzanine_create, name='mezzanine-create'),
    path('mezzanine/manage/<int:pk>/', views.mezzanine_update, name='mezzanine-update'),
    path('mezzanine/manage/<int:pk>/delete/', views.mezzanine_delete, name='mezzanine-delete'),
]
