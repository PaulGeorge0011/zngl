import logging
from datetime import date, timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    NightShiftCategory, NightShiftCheckItem, NightShiftDuty,
    NightShiftRecord, NightShiftCheckResult, NightShiftIssue,
)
from .nightshift_serializers import (
    NightShiftCategorySerializer, NightShiftCategoryListSerializer,
    NightShiftCheckItemSerializer, NightShiftDutySerializer,
    NightShiftRecordListSerializer, NightShiftRecordDetailSerializer,
)
from .permissions import IsSafetyOfficer
from .sms import notify_duty_assigned

logger = logging.getLogger(__name__)


# ── 分类 CRUD ────────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def category_list_create(request):
    if request.method == 'GET':
        qs = NightShiftCategory.objects.prefetch_related('items').all()
        active_only = request.query_params.get('active')
        if active_only == 'true':
            qs = qs.filter(is_active=True)
        return Response(NightShiftCategoryListSerializer(qs, many=True).data)

    if not IsSafetyOfficer().has_permission(request, None):
        return Response({'detail': '只有安全员可以执行此操作'}, status=status.HTTP_403_FORBIDDEN)
    ser = NightShiftCategorySerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(NightShiftCategorySerializer(ser.instance).data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsSafetyOfficer])
def category_detail(request, pk):
    try:
        cat = NightShiftCategory.objects.get(pk=pk)
    except NightShiftCategory.DoesNotExist:
        return Response({'detail': '分类不存在'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        ser = NightShiftCategorySerializer(cat, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(NightShiftCategorySerializer(ser.instance).data)

    cat.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── 检查项 CRUD ──────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def item_list_create(request, category_pk):
    try:
        cat = NightShiftCategory.objects.get(pk=category_pk)
    except NightShiftCategory.DoesNotExist:
        return Response({'detail': '分类不存在'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        items = cat.items.all()
        active_only = request.query_params.get('active')
        if active_only == 'true':
            items = items.filter(is_active=True)
        return Response(NightShiftCheckItemSerializer(items, many=True).data)

    if not IsSafetyOfficer().has_permission(request, None):
        return Response({'detail': '只有安全员可以执行此操作'}, status=status.HTTP_403_FORBIDDEN)
    ser = NightShiftCheckItemSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    ser.save(category=cat)
    return Response(ser.data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsSafetyOfficer])
def item_detail(request, category_pk, item_pk):
    try:
        item = NightShiftCheckItem.objects.get(pk=item_pk, category_id=category_pk)
    except NightShiftCheckItem.DoesNotExist:
        return Response({'detail': '检查项不存在'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        ser = NightShiftCheckItemSerializer(item, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    item.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── 排班 CRUD ────────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def duty_list_create(request):
    if request.method == 'GET':
        qs = NightShiftDuty.objects.select_related('inspector', 'created_by', 'record').all()
        month = request.query_params.get('month')
        if month:
            try:
                year, m = month.split('-')
                qs = qs.filter(duty_date__year=int(year), duty_date__month=int(m))
            except (ValueError, IndexError):
                pass
        duty_status = request.query_params.get('status')
        if duty_status:
            qs = qs.filter(status=duty_status)
        return Response(NightShiftDutySerializer(qs, many=True).data)

    if not IsSafetyOfficer().has_permission(request, None):
        return Response({'detail': '只有安全员可以执行此操作'}, status=status.HTTP_403_FORBIDDEN)

    dates = request.data.get('dates', [])
    inspector_id = request.data.get('inspector')
    if not inspector_id:
        return Response({'detail': '请指定检查人'}, status=status.HTTP_400_BAD_REQUEST)
    if not dates:
        single_date = request.data.get('duty_date')
        if single_date:
            dates = [single_date]
    if not dates:
        return Response({'detail': '请指定值班日期'}, status=status.HTTP_400_BAD_REQUEST)

    created = []
    for d in dates:
        if NightShiftDuty.objects.filter(duty_date=d).exists():
            continue
        duty = NightShiftDuty.objects.create(
            duty_date=d,
            inspector_id=inspector_id,
            created_by=request.user,
        )
        created.append(duty)

    # 触发短信提醒 (异步、失败不影响排班创建)
    for duty in created:
        try:
            notify_duty_assigned(duty)
        except Exception:
            logger.exception('notify_duty_assigned failed for duty %s', duty.pk)

    qs = NightShiftDuty.objects.select_related('inspector', 'created_by', 'record').filter(
        id__in=[d.id for d in created]
    )
    return Response(NightShiftDutySerializer(qs, many=True).data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsSafetyOfficer])
def duty_detail(request, pk):
    try:
        duty = NightShiftDuty.objects.select_related('inspector', 'created_by', 'record').get(pk=pk)
    except NightShiftDuty.DoesNotExist:
        return Response({'detail': '排班不存在'}, status=status.HTTP_404_NOT_FOUND)

    if duty.status == 'completed':
        return Response({'detail': '已完成的排班不可修改'}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'PUT':
        new_date = request.data.get('duty_date')
        new_inspector = request.data.get('inspector')
        date_changed = False
        inspector_changed = False
        if new_date and str(new_date) != str(duty.duty_date):
            conflict = NightShiftDuty.objects.filter(duty_date=new_date).exclude(pk=pk).exists()
            if conflict:
                return Response({'detail': f'{new_date} 已有排班'}, status=status.HTTP_400_BAD_REQUEST)
            duty.duty_date = new_date
            date_changed = True
        if new_inspector and int(new_inspector) != duty.inspector_id:
            duty.inspector_id = new_inspector
            inspector_changed = True
        # 如果发生实质变更，重置短信通知状态，重新发送
        if date_changed or inspector_changed:
            duty.sms_sent_at = None
        duty.save()
        duty.refresh_from_db()
        if date_changed or inspector_changed:
            try:
                notify_duty_assigned(duty)
            except Exception:
                logger.exception('notify_duty_assigned failed for duty %s', duty.pk)
        return Response(NightShiftDutySerializer(duty).data)

    duty.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── 今日巡检状态 ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def today_status(request):
    """当前用户今日的排班和检查状态"""
    today = date.today()
    duty = NightShiftDuty.objects.select_related('inspector', 'record').filter(
        duty_date=today,
    ).first()

    if not duty:
        return Response({
            'has_duty_today': False,
            'is_my_duty': False,
            'duty': None,
        })

    return Response({
        'has_duty_today': True,
        'is_my_duty': duty.inspector_id == request.user.id,
        'duty': NightShiftDutySerializer(duty).data,
    })


# ── 提交巡检记录 ─────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_create(request):
    duty_id = request.data.get('duty_id')
    if not duty_id:
        return Response({'detail': '缺少排班信息'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        duty = NightShiftDuty.objects.get(pk=duty_id)
    except NightShiftDuty.DoesNotExist:
        return Response({'detail': '排班不存在'}, status=status.HTTP_404_NOT_FOUND)

    if duty.inspector_id != request.user.id:
        return Response({'detail': '您不是该排班指定的检查人'}, status=status.HTTP_403_FORBIDDEN)

    if duty.status == 'completed':
        return Response({'detail': '该排班已完成检查'}, status=status.HTTP_400_BAD_REQUEST)

    results_data = request.data.get('results', [])
    issues_data = request.data.get('issues', [])
    overall_remark = request.data.get('overall_remark', '')

    has_issues = len(issues_data) > 0
    has_abnormal = any(not r.get('is_normal', True) for r in results_data)

    record = NightShiftRecord.objects.create(
        duty=duty,
        inspector=request.user,
        inspection_date=duty.duty_date,
        status='submitted',
        has_issues=has_issues or has_abnormal,
        overall_remark=overall_remark,
        submitted_at=timezone.now(),
    )

    active_categories = set(NightShiftCategory.objects.filter(is_active=True).values_list('id', flat=True))

    for r in results_data:
        cat_id = r.get('category')
        if cat_id not in active_categories:
            continue
        item_id = r.get('item')
        NightShiftCheckResult.objects.create(
            record=record,
            category_id=cat_id,
            item_id=item_id if item_id else None,
            custom_name=r.get('custom_name', ''),
            is_normal=r.get('is_normal', True),
            remark=r.get('remark', ''),
        )

    for issue in issues_data:
        desc = issue.get('description', '').strip()
        if not desc:
            continue
        NightShiftIssue.objects.create(
            record=record,
            description=desc,
            rectification=issue.get('rectification', ''),
            is_resolved=issue.get('is_resolved', False),
        )

    duty.status = 'completed'
    duty.record = record
    duty.save()

    return Response(
        NightShiftRecordDetailSerializer(record).data,
        status=status.HTTP_201_CREATED,
    )


# ── 记录列表 & 详情 ──────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def record_list(request):
    qs = NightShiftRecord.objects.select_related('inspector').filter(status='submitted')

    date_from = request.query_params.get('date_from')
    if date_from:
        qs = qs.filter(inspection_date__gte=date_from)
    date_to = request.query_params.get('date_to')
    if date_to:
        qs = qs.filter(inspection_date__lte=date_to)
    has_issues = request.query_params.get('has_issues')
    if has_issues == 'true':
        qs = qs.filter(has_issues=True)

    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    total = qs.count()
    records = qs[(page - 1) * page_size: page * page_size]

    return Response({
        'count': total,
        'page': page,
        'page_size': page_size,
        'results': NightShiftRecordListSerializer(records, many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def record_detail(request, pk):
    try:
        record = NightShiftRecord.objects.select_related('inspector').prefetch_related(
            'results__category', 'results__item', 'issues'
        ).get(pk=pk)
    except NightShiftRecord.DoesNotExist:
        return Response({'detail': '记录不存在'}, status=status.HTTP_404_NOT_FOUND)
    return Response(NightShiftRecordDetailSerializer(record).data)


# ── 概览统计 ─────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def overview(request):
    today = date.today()

    today_duty = NightShiftDuty.objects.select_related(
        'inspector', 'record'
    ).filter(duty_date=today).first()

    upcoming = NightShiftDuty.objects.select_related('inspector').filter(
        duty_date__gte=today, status='pending',
    ).order_by('duty_date')[:5]

    recent_completed = NightShiftDuty.objects.select_related(
        'inspector', 'record'
    ).filter(status='completed').order_by('-duty_date')[:5]

    thirty_days_ago = today - timedelta(days=30)
    total_duties = NightShiftDuty.objects.filter(duty_date__gte=thirty_days_ago, duty_date__lte=today).count()
    completed_duties = NightShiftDuty.objects.filter(duty_date__gte=thirty_days_ago, duty_date__lte=today, status='completed').count()

    result = {
        'today': today.isoformat(),
        'today_duty': NightShiftDutySerializer(today_duty).data if today_duty else None,
        'upcoming': NightShiftDutySerializer(upcoming, many=True).data,
        'recent_completed': NightShiftDutySerializer(recent_completed, many=True).data,
        'stats_30d': {
            'total': total_duties,
            'completed': completed_duties,
        },
    }

    if today_duty and today_duty.record:
        rec = today_duty.record
        total_checks = rec.results.count()
        abnormal_checks = rec.results.filter(is_normal=False).count()
        total_issues = rec.issues.count()
        resolved_issues = rec.issues.filter(is_resolved=True).count()
        result['check_stats'] = {
            'total': total_checks,
            'normal': total_checks - abnormal_checks,
            'abnormal': abnormal_checks,
        }
        result['issue_stats'] = {
            'total': total_issues,
            'resolved': resolved_issues,
            'unresolved': total_issues - resolved_issues,
        }
        result['recent_issues'] = [
            {'description': i.description, 'rectification': i.rectification, 'is_resolved': i.is_resolved}
            for i in rec.issues.all()[:10]
        ]
    else:
        result['check_stats'] = {'total': 0, 'normal': 0, 'abnormal': 0}
        result['issue_stats'] = {'total': 0, 'resolved': 0, 'unresolved': 0}
        result['recent_issues'] = []

    return Response(result)
