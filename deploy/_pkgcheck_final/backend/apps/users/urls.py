from django.urls import path
from . import views

urlpatterns = [
    # 认证
    path('login/', views.login_view, name='users-login'),
    path('logout/', views.logout_view, name='users-logout'),
    path('me/', views.me_view, name='users-me'),
    path('list/', views.user_list_view, name='users-list'),

    # SSO 云南中烟登录
    path('sso/login/', views.sso_login_view, name='users-sso-login'),
    path('sso/callback/', views.sso_callback_view, name='users-sso-callback'),

    # 用户管理（GET=所有人, POST=安��员）
    path('manage/', views.manage_list_create, name='users-manage'),
    # 以下接口均需安全员权限
    path('manage/<int:pk>/', views.manage_update, name='users-manage-update'),
    path('manage/<int:pk>/toggle/', views.manage_toggle, name='users-manage-toggle'),
    path('manage/<int:pk>/reset-password/', views.manage_reset_password, name='users-manage-reset-password'),
]
