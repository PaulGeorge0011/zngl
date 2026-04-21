import logging
from datetime import date

from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    DustRoom, InspectionTemplate, InspectionItem,
    DustRoomInspector, InspectionRecord, InspectionItemResult,
    INSPECTION_ROLE_CHOICES,
)
from .dustroom_serializers import (
    DustRoomSerializer,
    InspectionTemplateSerializer, InspectionTemplateListSerializer,
    InspectionItemSerializer,
    DustRoomInspectorSerializer,
    InspectionRecordListSerializer, InspectionRecordDetailSerializer,
    InspectionItemResultSerializer,
)
from .permissions import IsSafetyOfficer, IsDustRoomInspector

logger = logging.getLogger(__name__)

ROLE_DISPLAY = dict(INSPECTION_ROLE_CHOICES)


# ── 除尘房 CRUD ──────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def room_list_create(request):
    if request.method == 'GET':
        qs = DustRoom.objects.all()
        active_only = request.query_params.get('active')
        if active_only == 'true':
            qs = qs.filter(is_active=True)
        return Response(DustRoomSerializer(qs, many=True).data)

    if not IsSafetyOfficer().has_permission(request, None):
        return Response({'detail': '只有安全员可以执行此操作'}, status=status.HTTP_403_FORBIDDEN)
    ser = DustRoomSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsSafetyOfficer])
def room_detail(request, pk):
    try:
        room = DustRoom.objects.get(pk=pk)
    except DustRoom.DoesNotExist:
        return Response({'detail': '除尘房不存在'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        ser = DustRoomSerializer(room, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    room.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── 巡检模板 CRUD ────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def template_list_create(request):
    if request.method == 'GET':
        qs = InspectionTemplate.objects.prefetch_related('items').all()
        return Response(InspectionTemplateListSerializer(qs, many=True).data)

    if not IsSafetyOfficer().has_permission(request, None):
        return Response({'detail': '只有安全员可以执行此操作'}, status=status.HTTP_403_FORBIDDEN)
    ser = InspectionTemplateSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(InspectionTemplateSerializer(ser.instance).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def template_detail(request, pk):
    try:
        tpl = InspectionTemplate.objects.prefetch_related('items').get(pk=pk)
    except InspectionTemplate.DoesNotExist:
        return Response({'detail': '模板不存在'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(InspectionTemplateSerializer(tpl).data)

    if not IsSafetyOfficer().has_permission(request, None):
        return Response({'detail': '只有安全员可以执行此操作'}, status=status.HTTP_403_FORBIDDEN)
    ser = InspectionTemplateSerializer(tpl, data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(InspectionTemplateSerializer(ser.instance).data)


# ── 检查项 CRUD ──────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def item_list_create(request, template_pk):
    try:
        tpl = InspectionTemplate.objects.get(pk=template_pk)
    except InspectionTemplate.DoesNotExist:
        return Response({'detail': '模板不存在'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        items = tpl.items.all()
        return Response(InspectionItemSerializer(items, many=True).data)

    if not IsSafetyOfficer().has_permission(request, None):
        return Response({'detail': '只有安全员可以执行此操作'}, status=status.HTTP_403_FORBIDDEN)
    ser = InspectionItemSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    ser.save(template=tpl)
    return Response(ser.data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsSafetyOfficer])
def item_detail(request, template_pk, item_pk):
    try:
        item = InspectionItem.objects.get(pk=item_pk, template_id=template_pk)
    except InspectionItem.DoesNotExist:
        return Response({'detail': '检查项不存在'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        ser = InspectionItemSerializer(item, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    item.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── 巡检人员管理 ─────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def inspector_list_create(request):
    if request.method == 'GET':
        qs = DustRoomInspector.objects.select_related('user').all()
        role_filter = request.query_params.get('role')
        if role_filter:
            qs = qs.filter(role=role_filter)
        return Response(DustRoomInspectorSerializer(qs, many=True).data)

    if not IsSafetyOfficer().has_permission(request, None):
        return Response({'detail': '只有安全员可以执行此操作'}, status=status.HTTP_403_FORBIDDEN)
    ser = DustRoomInspectorSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(DustRoomInspectorSerializer(ser.instance).data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsSafetyOfficer])
def inspector_delete(request, pk):
    try:
        inspector = DustRoomInspector.objects.get(pk=pk)
    except DustRoomInspector.DoesNotExist:
        return Response({'detail': '记录不存在'}, status=status.HTTP_404_NOT_FOUND)
    inspector.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── 我的巡检任务 ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_tasks(request):
    """返回当前用户今日待完成的巡检任务"""
    roles = DustRoomInspector.objects.filter(user=request.user).values_list('role', flat=True)
    if not roles:
        return Response({'roles': [], 'tasks': []})

    today = date.today()
    rooms = DustRoom.objects.filter(is_active=True)
    templates = InspectionTemplate.objects.filter(role__in=roles, is_active=True)

    tasks = []
    for tpl in templates:
        for room in rooms:
            record = InspectionRecord.objects.filter(
                dust_room=room, template=tpl,
                inspector=request.user, inspection_date=today,
                status='submitted',
            ).first()
            tasks.append({
                'dust_room': DustRoomSerializer(room).data,
                'template_id': tpl.id,
                'role': tpl.role,
                'role_display': tpl.get_role_display(),
                'completed': record is not None,
                'record_id': record.id if record else None,
                'has_abnormal': record.has_abnormal if record else False,
            })

    return Response({
        'roles': [{'role': r, 'role_display': ROLE_DISPLAY.get(r, r)} for r in roles],
        'tasks': tasks,
    })


# ── 巡检记录提交 ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsDustRoomInspector])
def record_create(request):
    """提交巡检记录"""
    dust_room_id = request.data.get('dust_room')
    template_id = request.data.get('template')
    results_data = request.data.get('results', [])
    remark = request.data.get('remark', '')

    try:
        room = DustRoom.objects.get(pk=dust_room_id, is_active=True)
    except DustRoom.DoesNotExist:
        return Response({'detail': '除尘房不存在或已停用'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        tpl = InspectionTemplate.objects.get(pk=template_id, is_active=True)
    except InspectionTemplate.DoesNotExist:
        return Response({'detail': '模板不存在或已停用'}, status=status.HTTP_400_BAD_REQUEST)

    if not DustRoomInspector.objects.filter(user=request.user, role=tpl.role).exists():
        return Response({'detail': '您没有该角色的巡检权限'}, status=status.HTTP_403_FORBIDDEN)

    today = date.today()
    if InspectionRecord.objects.filter(
        dust_room=room, template=tpl, inspector=request.user,
        inspection_date=today, status='submitted',
    ).exists():
        return Response({'detail': '今日该除尘房已完成此角色的巡检'}, status=status.HTTP_400_BAD_REQUEST)

    has_abnormal = any(not r.get('is_normal', True) for r in results_data)

    record = InspectionRecord.objects.create(
        dust_room=room,
        template=tpl,
        inspector=request.user,
        inspection_date=today,
        status='submitted',
        has_abnormal=has_abnormal,
        remark=remark,
        submitted_at=timezone.now(),
    )

    valid_item_ids = set(tpl.items.values_list('id', flat=True))
    for r in results_data:
        item_id = r.get('item')
        if item_id not in valid_item_ids:
            continue
        InspectionItemResult.objects.create(
            record=record,
            item_id=item_id,
            value=str(r.get('value', '')),
            is_normal=r.get('is_normal', True),
            remark=r.get('remark', ''),
        )

    return Response(
        InspectionRecordDetailSerializer(record).data,
        status=status.HTTP_201_CREATED,
    )


# ── 巡检记录列表 & 详情 ──────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def record_list(request):
    qs = InspectionRecord.objects.select_related(
        'dust_room', 'template', 'inspector'
    ).filter(status='submitted')

    dust_room = request.query_params.get('dust_room')
    if dust_room:
        qs = qs.filter(dust_room_id=dust_room)

    role = request.query_params.get('role')
    if role:
        qs = qs.filter(template__role=role)

    date_from = request.query_params.get('date_from')
    if date_from:
        qs = qs.filter(inspection_date__gte=date_from)

    date_to = request.query_params.get('date_to')
    if date_to:
        qs = qs.filter(inspection_date__lte=date_to)

    has_abnormal = request.query_params.get('has_abnormal')
    if has_abnormal == 'true':
        qs = qs.filter(has_abnormal=True)

    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    total = qs.count()
    records = qs[(page - 1) * page_size: page * page_size]

    return Response({
        'count': total,
        'page': page,
        'page_size': page_size,
        'results': InspectionRecordListSerializer(records, many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def record_detail(request, pk):
    try:
        record = InspectionRecord.objects.select_related(
            'dust_room', 'template', 'inspector'
        ).prefetch_related('results__item').get(pk=pk)
    except InspectionRecord.DoesNotExist:
        return Response({'detail': '记录不存在'}, status=status.HTTP_404_NOT_FOUND)
    return Response(InspectionRecordDetailSerializer(record).data)


# ── 概览统计 ─────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def overview(request):
    """安全概览页除尘房状态汇总"""
    today = date.today()
    rooms = DustRoom.objects.filter(is_active=True)
    rooms_total = rooms.count()
    templates = InspectionTemplate.objects.filter(is_active=True)

    completion_by_role = []
    for tpl in templates:
        inspector_count = DustRoomInspector.objects.filter(role=tpl.role).count()
        if inspector_count == 0:
            continue
        expected = rooms_total
        completed = InspectionRecord.objects.filter(
            template=tpl, inspection_date=today, status='submitted',
        ).values('dust_room').distinct().count()
        completion_by_role.append({
            'role': tpl.role,
            'role_display': tpl.get_role_display(),
            'expected': expected,
            'completed': completed,
        })

    abnormal_records = InspectionRecord.objects.filter(
        inspection_date=today, status='submitted', has_abnormal=True,
    ).select_related('dust_room', 'template', 'inspector')

    recent_abnormals = []
    for rec in abnormal_records[:10]:
        abnormal_items = rec.results.filter(is_normal=False).select_related('item')
        for ai in abnormal_items:
            recent_abnormals.append({
                'room_name': rec.dust_room.name,
                'item_name': ai.item.name,
                'inspector': rec.inspector.get_full_name() or rec.inspector.username,
                'time': rec.submitted_at.strftime('%H:%M') if rec.submitted_at else '',
                'remark': ai.remark,
            })

    abnormal_count = InspectionItemResult.objects.filter(
        record__inspection_date=today,
        record__status='submitted',
        is_normal=False,
    ).count()

    return Response({
        'today': today.isoformat(),
        'rooms_total': rooms_total,
        'completion_by_role': completion_by_role,
        'abnormal_count': abnormal_count,
        'recent_abnormals': recent_abnormals[:20],
    })
