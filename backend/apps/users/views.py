import logging
import re
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings as django_settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import redirect as django_redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from apps.safety.permissions import IsSafetyOfficer
from .models import UserProfile
from .serializers import (
    UserManageSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    ResetPasswordSerializer,
)
from .services.sso import (
    build_authorize_url,
    consume_login_state,
    exchange_code_for_token,
    fetch_userinfo,
    introspect_access_token,
    normalize_userinfo,
    register_login_state,
)
from .services.user_provisioning import provision_user_from_sso

logger = logging.getLogger(__name__)


def _user_data(user):
    """Return serializable dict for a User.

    IMPORTANT: Django's built-in User has no 'role' field.
    We synthesize it here from group membership (安全员 > 班组长 > 员工).
    This is what the frontend UserInfo.role stores and uses for permission checks.
    """
    groups = list(user.groups.values_list('name', flat=True))
    # Determine primary role (安全员 > 班组长 > 员工)
    if '安全员' in groups:
        role = 'safety_officer'
    elif '班组长' in groups:
        role = 'team_leader'
    else:
        role = 'worker'
    return {
        'id': user.id,
        'username': user.username,
        'display_name': user.get_full_name() or user.username,
        'role': role,
        'is_assigner': '整改分派人' in groups,  # 整改分派权限
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    if not username or not password:
        return Response({'error': '请输入用户名和密码'}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({'error': '用户名或密码错误'}, status=401)
    if not user.is_active:
        return Response({'error': '账号已禁用'}, status=403)

    login(request, user)
    logger.info(f"User {username} logged in")
    return Response(_user_data(user))


@api_view(['POST'])
@permission_classes([AllowAny])
def logout_view(request):
    logout(request)
    return Response({'message': '已退出登录'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(_user_data(request.user))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list_view(request):
    """List users. Supports ?role=班组长 filter."""
    role_filter = request.query_params.get('role')
    qs = User.objects.filter(is_active=True).prefetch_related('groups')
    if role_filter:
        qs = qs.filter(groups__name=role_filter)
    return Response([_user_data(u) for u in qs])


# ── 用户管理（安全员专用写操作，所有人可读）────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_list_create(request):
    """
    GET  — 列出所有用户（已登录用户均可）
    POST — 创建新用户（仅安全员）
    """
    if request.method == 'GET':
        return _manage_list(request)

    # POST：仅安全员
    if not IsSafetyOfficer().has_permission(request, None):
        return Response({'error': '只有安全员可以创建用户'}, status=403)
    return _manage_create(request)


def _manage_list(request):
    search = request.query_params.get('search', '').strip()
    qs = User.objects.prefetch_related('groups', 'profile').order_by('id')
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search) |
            Q(username__icontains=search) |
            Q(profile__employee_id__icontains=search)
        )
    return Response(UserManageSerializer(qs, many=True).data)


def _manage_create(request):
    serializer = UserCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    logger.info(f"用户创建: {user.username} by {request.user.username}")
    return Response(UserManageSerializer(user).data, status=201)


@api_view(['PUT'])
@permission_classes([IsSafetyOfficer])
def manage_update(request, pk):
    """编辑用户信息（姓名、角色、工号、电话）"""
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': '用户不存在'}, status=404)

    serializer = UserUpdateSerializer(data=request.data, context={'user': user})
    serializer.is_valid(raise_exception=True)
    serializer.update(user, serializer.validated_data)
    logger.info(f"用户编辑: {user.username} by {request.user.username}")
    return Response(UserManageSerializer(user).data)


@api_view(['PATCH'])
@permission_classes([IsSafetyOfficer])
def manage_toggle(request, pk):
    """切换用户启用/禁用状态"""
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': '用户不存在'}, status=404)

    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    action = '启用' if user.is_active else '禁用'
    logger.info(f"用户{action}: {user.username} by {request.user.username}")
    return Response(UserManageSerializer(user).data)


@api_view(['POST'])
@permission_classes([IsSafetyOfficer])
def manage_reset_password(request, pk):
    """重置用户密码"""
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'error': '用户不存在'}, status=404)

    serializer = ResetPasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user.set_password(serializer.validated_data['password'])
    user.save(update_fields=['password'])
    logger.info(f"密码重置: {user.username} by {request.user.username}")
    return Response({'message': '密码已重置'})


# ── SSO 云南中烟登录 ────────────────────────────────────────────────────────────

_SAFE_NEXT_RE = re.compile(r'^/[a-zA-Z0-9_./-]*$')
_TRUSTED_LOOPBACK_HOSTS = {'localhost', '127.0.0.1', '::1', 'testserver'}
_REQUEST_ORIGIN_LOOPBACK_HOSTS = {'localhost', '127.0.0.1', '::1'}


def _request_host_name(request) -> str:
    host = request.get_host().strip().lower()
    if host.startswith('[') and ']' in host:
        return host[1:host.index(']')]
    if host.count(':') == 1:
        return host.split(':', 1)[0]
    return host


def _is_loopback_request(request) -> bool:
    return _request_host_name(request) in _TRUSTED_LOOPBACK_HOSTS


def _should_use_request_origin(request) -> bool:
    return bool(request) and _request_host_name(request) in _REQUEST_ORIGIN_LOOPBACK_HOSTS and not request.is_secure()


def _resolve_sso_redirect_uri(request) -> str:
    configured = (getattr(django_settings, 'SSO_REDIRECT_URI', '') or '').strip()
    if configured and not _should_use_request_origin(request):
        return configured

    dev_backend_base = (getattr(django_settings, 'APP_DEV_BACKEND_BASE_URL', '') or '').strip()
    if dev_backend_base:
        return f"{_normalize_base_url(dev_backend_base)}/api/users/sso/callback/"

    return 'http://localhost:8000/api/users/sso/callback/'


def _is_potentially_trustworthy_request(request) -> bool:
    return request.is_secure() or _is_loopback_request(request)


def _normalize_base_url(url: str) -> str:
    return url.rstrip('/')


def _resolve_local_frontend_base(request) -> str:
    for header in ('HTTP_ORIGIN', 'HTTP_REFERER'):
        raw = (request.META.get(header) or '').strip()
        if not raw:
            continue
        parts = urlsplit(raw)
        if parts.scheme in {'http', 'https'} and parts.netloc:
            return _normalize_base_url(f'{parts.scheme}://{parts.netloc}')

    configured = (getattr(django_settings, 'APP_DEV_BASE_URL', '') or '').strip()
    if configured:
        return _normalize_base_url(configured)

    cors_origins = list(getattr(django_settings, 'CORS_ALLOWED_ORIGINS', []) or [])
    for origin in cors_origins:
        if 'localhost' in origin or '127.0.0.1' in origin:
            return _normalize_base_url(origin)

    return 'http://localhost:3001'


def _app_path(path: str, request=None) -> str:
    if request and _should_use_request_origin(request):
        frontend_base = _resolve_local_frontend_base(request)
        return f'{frontend_base}{path}'

    external_base = (getattr(django_settings, 'APP_EXTERNAL_BASE_URL', '') or '').strip()
    if not external_base:
        return path

    parts = urlsplit(external_base)
    target = urlsplit(path)
    base_path = parts.path.rstrip('/')
    final_path = f'{base_path}{target.path}' if base_path else target.path
    return urlunsplit((parts.scheme, parts.netloc, final_path, target.query, target.fragment))


def _safe_next(raw):
    if raw and _SAFE_NEXT_RE.match(raw) and not raw.startswith('//'):
        return raw
    return '/dashboard'


def _sso_error_redirect(error_code: str, request=None) -> django_redirect:
    return django_redirect(_app_path(f'/login?sso_error={error_code}', request=request))


@api_view(['GET'])
@permission_classes([AllowAny])
def sso_login_view(request):
    if not getattr(django_settings, 'SSO_ENABLED', False):
        return _sso_error_redirect('disabled', request=request)

    if not _is_potentially_trustworthy_request(request):
        logger.warning('Rejected SSO login from untrustworthy origin: %s', request.build_absolute_uri('/'))
        return _sso_error_redirect('origin_untrusted', request=request)

    next_path = _safe_next(request.query_params.get('next'))
    redirect_uri = _resolve_sso_redirect_uri(request)
    state = register_login_state(request.session, next_path=next_path, redirect_uri=redirect_uri)
    state_payload = request.session.get('sso_login_states', {}).get(state, {})
    authorize_url = build_authorize_url(
        state,
        nonce=state_payload.get('nonce'),
        redirect_uri=state_payload.get('redirect_uri'),
    )
    return django_redirect(authorize_url)


@api_view(['GET'])
@permission_classes([AllowAny])
def sso_callback_view(request):
    code = request.query_params.get('code', '').strip()
    state = request.query_params.get('state', '').strip()

    if not code:
        return _sso_error_redirect('code_missing', request=request)

    state_payload = consume_login_state(request.session, state)
    if state_payload is None:
        return _sso_error_redirect('state_invalid', request=request)

    next_path = _safe_next(state_payload.get('next_path'))
    redirect_uri = (state_payload.get('redirect_uri') or _resolve_sso_redirect_uri(request)).strip()

    try:
        token_data = exchange_code_for_token(code, redirect_uri=redirect_uri)
    except Exception:
        logger.exception('SSO token exchange failed')
        return _sso_error_redirect('token_exchange_failed', request=request)

    access_token = token_data.get('access_token')
    if not access_token:
        return _sso_error_redirect('token_exchange_failed', request=request)

    introspect_url = (getattr(django_settings, 'SSO_INTROSPECT_URL', '') or '').strip()
    if introspect_url:
        try:
            introspect_payload = introspect_access_token(access_token)
        except Exception:
            logger.exception('SSO token introspection failed')
            return _sso_error_redirect('token_exchange_failed', request=request)
        if not introspect_payload.get('active'):
            logger.warning('SSO access token is inactive')
            return _sso_error_redirect('token_exchange_failed', request=request)

    try:
        raw_userinfo = fetch_userinfo(access_token)
    except Exception:
        logger.exception('SSO userinfo fetch failed')
        return _sso_error_redirect('userinfo_failed', request=request)

    try:
        sso_user_info = normalize_userinfo(raw_userinfo)
    except ValueError:
        logger.warning('SSO userinfo missing employee_id')
        return _sso_error_redirect('employee_id_missing', request=request)

    user = provision_user_from_sso(sso_user_info)

    if not user.is_active:
        return _sso_error_redirect('account_disabled', request=request)

    login(request, user)
    logger.info(f"SSO login: {user.username} (employee_id={sso_user_info.employee_id})")
    return django_redirect(_app_path(next_path, request=request))
