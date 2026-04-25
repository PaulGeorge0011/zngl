"""整改中心 HTTP 接口。"""
from __future__ import annotations

import logging
from datetime import datetime

from django.contrib.auth.models import Group, User
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import rectification_service as svc
from .models import RectificationOrder, RectificationNotifyRecipient
from .permissions import IsSafetyOfficer
from .rectification_serializers import (
    RectificationDetailSerializer,
    RectificationListSerializer,
    RectificationNotifyRecipientSerializer,
)

logger = logging.getLogger(__name__)


def _is_safety_officer(user) -> bool:
    """安全员或超级用户"""
    return (
        user.is_authenticated
        and user.is_active
        and (user.is_superuser or user.groups.filter(name='安全员').exists())
    )

def _is_assigner(user) -> bool:
    """被授权的分派人"""
    return (
        user.is_authenticated
        and user.is_active
        and user.groups.filter(name='整改分派人').exists()
    )

def _can_assign_or_verify(user, order: RectificationOrder) -> bool:
    """
    权限层级：
    1. 超级用户/安全员：可分派/验证所有工单
    2. 整改分派人：可分派所有工单
    3. 指派的验证人：可分派/验证自己负责的工单
    """
    if _is_safety_officer(user):
        return True
    if _is_assigner(user):
        return True
    return bool(user.is_authenticated and order.verifier_id == user.id)

def _can_manage_assigners(user) -> bool:
    """只有超级用户和安全员可以管理分派人"""
    return _is_safety_officer(user)


# ── 查询 ─────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_list(request):
    """整改工单列表，支持多种过滤。"""
    qs = RectificationOrder.objects.select_related(
        'submitter', 'assignee', 'assigner', 'verifier',
    ).all()

    params = request.query_params
    if params.get('status'):
        qs = qs.filter(status=params['status'])
    if params.get('source_type'):
        qs = qs.filter(source_type=params['source_type'])
    if params.get('severity'):
        qs = qs.filter(severity=params['severity'])
    if params.get('assignee'):
        qs = qs.filter(assignee_id=params['assignee'])
    if params.get('submitter'):
        qs = qs.filter(submitter_id=params['submitter'])
    if params.get('overdue') == 'true':
        qs = qs.filter(overdue=True)
    if params.get('source_id'):
        qs = qs.filter(source_id=params['source_id'])

    date_from = params.get('date_from')
    date_to = params.get('date_to')
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    search = params.get('search', '').strip()
    if search:
        qs = qs.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    # 所有人可见所有工单 —— 整改全流程公开、公平、公正。
    # 不同角色的差异体现在 *能否操作*（在详情页的操作按钮上受控），不在可见范围。
    scope = params.get('scope', '')
    user = request.user
    if scope == 'assigned':
        qs = qs.filter(assignee=user)
    elif scope == 'submitted':
        qs = qs.filter(submitter=user)
    elif scope == 'to_verify':
        qs = qs.filter(status='verifying')
    elif scope == 'to_assign':
        qs = qs.filter(status='pending')

    page = int(params.get('page', 1))
    page_size = int(params.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size
    total = qs.count()
    items = qs[start:end]

    serializer = RectificationListSerializer(items, many=True, context={'request': request})
    return Response({
        'count': total,
        'page': page,
        'page_size': page_size,
        'results': serializer.data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_detail(request, pk):
    try:
        order = RectificationOrder.objects.select_related(
            'submitter', 'assignee', 'assigner', 'verifier',
        ).prefetch_related('images', 'logs__operator').get(pk=pk)
    except RectificationOrder.DoesNotExist:
        return Response({'error': '整改工单不存在'}, status=404)
    return Response(RectificationDetailSerializer(order, context={'request': request}).data)


# ── 状态流转 ────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def order_assign(request, pk):
    """分派整改责任人；安全员或指派验证人可操作。"""
    try:
        order = RectificationOrder.objects.get(pk=pk)
    except RectificationOrder.DoesNotExist:
        return Response({'error': '整改工单不存在'}, status=404)

    if not _can_assign_or_verify(request.user, order):
        return Response({'error': '您没有分派整改人的权限'}, status=403)

    assignee_id = request.data.get('assignee_id')
    if not assignee_id:
        return Response({'error': '请选择整改责任人'}, status=400)
    try:
        assignee = User.objects.get(pk=assignee_id)
    except User.DoesNotExist:
        return Response({'error': '责任人不存在'}, status=400)

    deadline_raw = request.data.get('deadline')
    deadline: datetime | None = None
    if deadline_raw:
        deadline = parse_datetime(deadline_raw)
        if deadline is None:
            return Response({'error': '期限格式错误，期望 ISO8601'}, status=400)
        if timezone.is_naive(deadline):
            deadline = timezone.make_aware(deadline)

    try:
        order = svc.assign(
            order,
            assignee=assignee,
            assigner=request.user,
            deadline=deadline,
            remark=request.data.get('remark', ''),
        )
    except svc.StateTransitionError as e:
        return Response({'error': str(e)}, status=400)

    logger.info('整改工单分派: id=%s by %s', order.id, request.user.username)
    return Response(RectificationDetailSerializer(order, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def order_reassign(request, pk):
    """改派整改责任人；安全员或指派验证人可操作。"""
    try:
        order = RectificationOrder.objects.get(pk=pk)
    except RectificationOrder.DoesNotExist:
        return Response({'error': '整改工单不存在'}, status=404)

    if not _can_assign_or_verify(request.user, order):
        return Response({'error': '您没有改派整改人的权限'}, status=403)

    assignee_id = request.data.get('assignee_id')
    try:
        assignee = User.objects.get(pk=assignee_id)
    except (User.DoesNotExist, TypeError, ValueError):
        return Response({'error': '责任人不存在'}, status=400)

    deadline_raw = request.data.get('deadline')
    deadline: datetime | None = None
    if deadline_raw:
        deadline = parse_datetime(deadline_raw)
        if deadline and timezone.is_naive(deadline):
            deadline = timezone.make_aware(deadline)

    try:
        order = svc.reassign(
            order,
            assignee=assignee,
            operator=request.user,
            deadline=deadline,
            remark=request.data.get('remark', ''),
        )
    except svc.StateTransitionError as e:
        return Response({'error': str(e)}, status=400)
    return Response(RectificationDetailSerializer(order, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def order_submit(request, pk):
    """整改责任人提交整改。"""
    try:
        order = RectificationOrder.objects.get(pk=pk)
    except RectificationOrder.DoesNotExist:
        return Response({'error': '整改工单不存在'}, status=404)

    rectify_description = request.data.get('rectify_description', '').strip()
    if not rectify_description:
        return Response({'error': '请填写整改说明'}, status=400)

    images = request.FILES.getlist('images')[:3]
    try:
        order = svc.submit_rectification(
            order,
            operator=request.user,
            rectify_description=rectify_description,
            images=images,
        )
    except PermissionError as e:
        return Response({'error': str(e)}, status=403)
    except (svc.StateTransitionError, ValueError) as e:
        return Response({'error': str(e)}, status=400)
    return Response(RectificationDetailSerializer(order, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def order_verify(request, pk):
    """验证整改结果；安全员或指派验证人可操作。"""
    try:
        order = RectificationOrder.objects.get(pk=pk)
    except RectificationOrder.DoesNotExist:
        return Response({'error': '整改工单不存在'}, status=404)

    if not _can_assign_or_verify(request.user, order):
        return Response({'error': '您没有验证整改的权限'}, status=403)

    action = request.data.get('action')
    if action not in ('approve', 'reject'):
        return Response({'error': 'action 必须为 approve 或 reject'}, status=400)
    remark = request.data.get('remark', '')

    try:
        order = svc.verify(
            order,
            operator=request.user,
            passed=(action == 'approve'),
            remark=remark,
        )
    except PermissionError as e:
        return Response({'error': str(e)}, status=403)
    except svc.StateTransitionError as e:
        return Response({'error': str(e)}, status=400)
    return Response(RectificationDetailSerializer(order, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsSafetyOfficer])
def order_cancel(request, pk):
    """取消工单（误报/重复）。"""
    try:
        order = RectificationOrder.objects.get(pk=pk)
    except RectificationOrder.DoesNotExist:
        return Response({'error': '整改工单不存在'}, status=404)

    remark = request.data.get('remark', '')
    try:
        order = svc.cancel(order, operator=request.user, remark=remark)
    except (svc.StateTransitionError, ValueError) as e:
        return Response({'error': str(e)}, status=400)
    return Response(RectificationDetailSerializer(order, context={'request': request}).data)


# ── 我的整改 / 统计 ─────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_rectifications(request):
    """整改工单看板计数。

    所有人都能看到 "待分派 / 待验证" 的全局数字（公开透明），
    是否"能操作"由 is_safety_officer 决定，前端据此控制按钮显隐。
    """
    user = request.user
    is_officer = user.groups.filter(name='安全员').exists() or user.is_superuser

    return Response({
        'to_fix': RectificationOrder.objects.filter(assignee=user, status='fixing').count(),
        'submitted': RectificationOrder.objects.filter(submitter=user).count(),
        'to_verify': RectificationOrder.objects.filter(status='verifying').count(),
        'to_assign': RectificationOrder.objects.filter(status='pending').count(),
        'is_safety_officer': is_officer,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def order_assign_verifier(request, pk):
    """分派验证人。安全员始终可操作；已指派验证人也可改派。"""
    try:
        order = RectificationOrder.objects.get(pk=pk)
    except RectificationOrder.DoesNotExist:
        return Response({'error': '整改工单不存在'}, status=404)

    if not _can_assign_or_verify(request.user, order):
        return Response({'error': '您没有分派验证人的权限'}, status=403)

    verifier_id = request.data.get('verifier_id')
    if not verifier_id:
        return Response({'error': '请选择验证人'}, status=400)
    try:
        verifier = User.objects.get(pk=verifier_id)
    except (User.DoesNotExist, TypeError, ValueError):
        return Response({'error': '验证人不存在'}, status=400)

    try:
        order = svc.assign_verifier(
            order, verifier=verifier, operator=request.user,
            remark=request.data.get('remark', ''),
        )
    except (svc.StateTransitionError, ValueError) as e:
        return Response({'error': str(e)}, status=400)
    return Response(RectificationDetailSerializer(order, context={'request': request}).data)


# ── 通知接收人配置 ──────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def notify_config_list_create(request):
    """列出 / 新增 整改新工单通知接收人。仅安全员可增删。"""
    if request.method == 'GET':
        qs = RectificationNotifyRecipient.objects.select_related('user__profile').all()
        return Response(
            RectificationNotifyRecipientSerializer(qs, many=True).data
        )

    if not _is_safety_officer(request.user):
        return Response({'error': '仅安全员可配置通知接收人'}, status=403)

    user_id = request.data.get('user_id')
    source_type = request.data.get('source_type', '') or ''
    if not user_id:
        return Response({'error': '请选择用户'}, status=400)
    try:
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, TypeError, ValueError):
        return Response({'error': '用户不存在'}, status=400)

    valid_sources = {'', 'hazard_report', 'dustroom_inspection', 'nightshift_check'}
    if source_type not in valid_sources:
        return Response({'error': '来源类型无效'}, status=400)

    obj, created = RectificationNotifyRecipient.objects.get_or_create(
        user=user, source_type=source_type,
        defaults={'enabled': True},
    )
    if not created and not obj.enabled:
        obj.enabled = True
        obj.save(update_fields=['enabled'])

    return Response(
        RectificationNotifyRecipientSerializer(obj).data,
        status=201 if created else 200,
    )


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def notify_config_detail(request, pk):
    """更新启用状态 / 删除 通知接收人。"""
    if not _is_safety_officer(request.user):
        return Response({'error': '仅安全员可配置通知接收人'}, status=403)
    try:
        obj = RectificationNotifyRecipient.objects.get(pk=pk)
    except RectificationNotifyRecipient.DoesNotExist:
        return Response({'error': '配置不存在'}, status=404)

    if request.method == 'DELETE':
        obj.delete()
        return Response(status=204)

    # PATCH: 仅支持切换 enabled
    if 'enabled' in request.data:
        obj.enabled = bool(request.data['enabled'])
        obj.save(update_fields=['enabled'])
    return Response(RectificationNotifyRecipientSerializer(obj).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def overview_stats(request):
    """整改中心概览统计。"""
    qs = RectificationOrder.objects.all()
    status_counts = dict(
        qs.values_list('status').annotate(c=Count('id')).values_list('status', 'c')
    )
    source_counts = dict(
        qs.values_list('source_type').annotate(c=Count('id')).values_list('source_type', 'c')
    )
    overdue_count = qs.filter(overdue=True).exclude(status__in=['closed', 'cancelled']).count()

    return Response({
        'total': qs.count(),
        'by_status': status_counts,
        'by_source': source_counts,
        'overdue': overdue_count,
    })


# ── 整改分派人管理 ──────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_assigners(request):
    """查询已授权的分派人列表"""
    if not _can_manage_assigners(request.user):
        return Response({'error': '无权限'}, status=403)

    group = Group.objects.filter(name='整改分派人').first()
    if not group:
        return Response({'assigners': []})

    assigners = []
    for user in group.user_set.select_related('profile').all():
        display_name = user.username
        if hasattr(user, 'profile') and user.profile:
            display_name = user.profile.real_name or user.username

        assigners.append({
            'id': user.id,
            'username': user.username,
            'display_name': display_name,
        })

    return Response({'assigners': assigners})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def grant_assigner(request):
    """授予分派权限"""
    if not _can_manage_assigners(request.user):
        return Response({'error': '无权限'}, status=403)

    user_id = request.data.get('user_id')
    if not user_id:
        return Response({'error': '缺少 user_id'}, status=400)

    try:
        user_id = int(user_id)
        user = User.objects.get(id=user_id)
        group, _ = Group.objects.get_or_create(name='整改分派人')
        user.groups.add(group)

        logger.info(f"用户 {request.user.username} 授予 {user.username} 整改分派权限")

        return Response({
            'success': True,
            'message': f'已授予 {user.username} 分派权限'
        })
    except (ValueError, TypeError):
        return Response({'error': 'user_id 格式错误'}, status=400)
    except User.DoesNotExist:
        return Response({'error': '用户不存在'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_assigner(request):
    """撤销分派权限"""
    if not _can_manage_assigners(request.user):
        return Response({'error': '无权限'}, status=403)

    user_id = request.data.get('user_id')
    if not user_id:
        return Response({'error': '缺少 user_id'}, status=400)

    try:
        user_id = int(user_id)
        user = User.objects.get(id=user_id)
        group = Group.objects.filter(name='整改分派人').first()
        if group:
            user.groups.remove(group)

        logger.info(f"用户 {request.user.username} 撤销 {user.username} 整改分派权限")

        return Response({
            'success': True,
            'message': f'已撤销 {user.username} 的分派权限'
        })
    except (ValueError, TypeError):
        return Response({'error': 'user_id 格式错误'}, status=400)
    except User.DoesNotExist:
        return Response({'error': '用户不存在'}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_assigner_candidates(request):
    """获取可授权的用户候选列表（排除已授权和管理员）"""
    if not _can_manage_assigners(request.user):
        return Response({'error': '无权限'}, status=403)

    # 获取已授权的分派人
    assigner_group = Group.objects.filter(name='整改分派人').first()
    existing_ids = list(assigner_group.user_set.values_list('id', flat=True)) if assigner_group else []

    # 获取安全员
    safety_group = Group.objects.filter(name='安全员').first()
    safety_ids = list(safety_group.user_set.values_list('id', flat=True)) if safety_group else []

    # 排除超级用户、安全员、已授权的分派人
    candidates = User.objects.filter(
        is_active=True
    ).exclude(
        id__in=existing_ids + safety_ids
    ).exclude(
        is_superuser=True
    ).select_related('profile')

    result = []
    for user in candidates:
        display_name = user.username
        if hasattr(user, 'profile') and user.profile:
            display_name = user.profile.real_name or user.username

        result.append({
            'id': user.id,
            'username': user.username,
            'display_name': display_name,
        })

    return Response({'candidates': result})
