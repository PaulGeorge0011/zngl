from django.urls import path
from . import views
from . import dustroom_views
from . import nightshift_views
from . import rectification_views

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

    # ── 除尘房巡检 ──────────────────────────────────────────────
    path('dustroom/rooms/', dustroom_views.room_list_create, name='dustroom-room-list'),
    path('dustroom/rooms/<int:pk>/', dustroom_views.room_detail, name='dustroom-room-detail'),

    path('dustroom/templates/', dustroom_views.template_list_create, name='dustroom-template-list'),
    path('dustroom/templates/<int:pk>/', dustroom_views.template_detail, name='dustroom-template-detail'),
    path('dustroom/templates/<int:template_pk>/items/', dustroom_views.item_list_create, name='dustroom-item-list'),
    path('dustroom/templates/<int:template_pk>/items/<int:item_pk>/', dustroom_views.item_detail, name='dustroom-item-detail'),

    path('dustroom/inspectors/', dustroom_views.inspector_list_create, name='dustroom-inspector-list'),
    path('dustroom/inspectors/<int:pk>/', dustroom_views.inspector_delete, name='dustroom-inspector-delete'),

    path('dustroom/my-tasks/', dustroom_views.my_tasks, name='dustroom-my-tasks'),
    path('dustroom/records/', dustroom_views.record_list, name='dustroom-record-list'),
    path('dustroom/records/create/', dustroom_views.record_create, name='dustroom-record-create'),
    path('dustroom/records/<int:pk>/', dustroom_views.record_detail, name='dustroom-record-detail'),
    path('dustroom/overview/', dustroom_views.overview, name='dustroom-overview'),

    # ── 夜班监护检查 ────────────────────────────────────────────
    path('nightshift/categories/', nightshift_views.category_list_create, name='nightshift-category-list'),
    path('nightshift/categories/<int:pk>/', nightshift_views.category_detail, name='nightshift-category-detail'),
    path('nightshift/categories/<int:category_pk>/items/', nightshift_views.item_list_create, name='nightshift-item-list'),
    path('nightshift/categories/<int:category_pk>/items/<int:item_pk>/', nightshift_views.item_detail, name='nightshift-item-detail'),

    path('nightshift/duties/', nightshift_views.duty_list_create, name='nightshift-duty-list'),
    path('nightshift/duties/<int:pk>/', nightshift_views.duty_detail, name='nightshift-duty-detail'),

    path('nightshift/today/', nightshift_views.today_status, name='nightshift-today'),
    path('nightshift/records/', nightshift_views.record_list, name='nightshift-record-list'),
    path('nightshift/records/create/', nightshift_views.record_create, name='nightshift-record-create'),
    path('nightshift/records/<int:pk>/', nightshift_views.record_detail, name='nightshift-record-detail'),
    path('nightshift/overview/', nightshift_views.overview, name='nightshift-overview'),
    path('nightshift/inspector-stats/', nightshift_views.inspector_stats, name='nightshift-inspector-stats'),

    # ── 整改中心（统一工单） ──────────────────────────────────────
    path('rectifications/', rectification_views.order_list, name='rect-list'),
    path('rectifications/my/', rectification_views.my_rectifications, name='rect-my'),
    path('rectifications/stats/', rectification_views.overview_stats, name='rect-stats'),
    path('rectifications/<int:pk>/', rectification_views.order_detail, name='rect-detail'),
    path('rectifications/<int:pk>/assign/', rectification_views.order_assign, name='rect-assign'),
    path('rectifications/<int:pk>/reassign/', rectification_views.order_reassign, name='rect-reassign'),
    path('rectifications/<int:pk>/assign-verifier/', rectification_views.order_assign_verifier, name='rect-assign-verifier'),
    path('rectifications/<int:pk>/submit/', rectification_views.order_submit, name='rect-submit'),
    path('rectifications/<int:pk>/verify/', rectification_views.order_verify, name='rect-verify'),
    path('rectifications/<int:pk>/cancel/', rectification_views.order_cancel, name='rect-cancel'),

    # 整改新工单通知接收人配置
    path('rectifications-notify-config/', rectification_views.notify_config_list_create, name='rect-notify-list'),
    path('rectifications-notify-config/<int:pk>/', rectification_views.notify_config_detail, name='rect-notify-detail'),
]
