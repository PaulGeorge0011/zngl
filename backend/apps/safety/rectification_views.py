"""整改中心 HTTP 接口。"""
from __future__ import annotations

import logging
from datetime import datetime

from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import rectification_service as svc
from .models import RectificationOrder
from .permissions import IsSafetyOfficer
from .rectification_serializers import (
    RectificationDetailSerializer,
    RectificationListSerializer,
)

logger = logging.getLogger(__name__)


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
@permission_classes([IsSafetyOfficer])
def order_assign(request, pk):
    """安全员分派整改责任人。"""
    try:
        order = RectificationOrder.objects.get(pk=pk)
    except RectificationOrder.DoesNotExist:
        return Response({'error': '整改工单不存在'}, status=404)

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
@permission_classes([IsSafetyOfficer])
def order_reassign(request, pk):
    """安全员改派整改责任人。"""
    try:
        order = RectificationOrder.objects.get(pk=pk)
    except RectificationOrder.DoesNotExist:
        return Response({'error': '整改工单不存在'}, status=404)

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
@permission_classes([IsSafetyOfficer])
def order_verify(request, pk):
    """安全员验证整改结果。"""
    try:
        order = RectificationOrder.objects.get(pk=pk)
    except RectificationOrder.DoesNotExist:
        return Response({'error': '整改工单不存在'}, status=404)

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
