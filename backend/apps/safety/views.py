import logging
import requests
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Location, HazardReport, HazardImage, RectificationOrder
from .serializers import (
    LocationSerializer,
    HazardCreateSerializer,
    HazardListSerializer,
    HazardDetailSerializer,
)
from .permissions import IsSafetyOfficer
from . import rectification_service as rect_svc

logger = logging.getLogger(__name__)


# ── Knowledge Base (existing) ─────────────────────────────────────────────────

@api_view(['POST'])
def search_knowledge(request):
    """
    查询 RAGflow 安全知识库
    请求体：{"question": "问题内容", "top_n": 5}
    """
    question = request.data.get('question', '').strip()
    if not question:
        return Response({'error': '请输入查询内容'}, status=400)

    top_n = int(request.data.get('top_n', 5))

    if not settings.RAGFLOW_API_KEY or not settings.RAGFLOW_BASE_URL:
        return Response({'error': 'RAGflow 未配置，请联系管理员'}, status=503)

    dataset_id = settings.RAGFLOW_SAFETY_DATASET_ID
    if not dataset_id:
        return Response({'error': '安全知识库未配置'}, status=503)

    url = f"{settings.RAGFLOW_BASE_URL}/api/v1/retrieval"
    headers = {
        "Authorization": f"Bearer {settings.RAGFLOW_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "question": question,
        "dataset_ids": [dataset_id],
        "top_n": top_n,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        chunks = data.get('data', {}).get('chunks', [])

        results = [
            {
                'content': c.get('content', ''),
                'document_name': c.get('document_keyword', '') or c.get('docnm_kwd', ''),
                'score': round(c.get('similarity', 0), 3),
            }
            for c in chunks
        ]

        logger.info(f"安全知识库查询: '{question}' 返回 {len(results)} 条")
        return Response({'question': question, 'results': results, 'total': len(results)})

    except requests.exceptions.ConnectionError:
        return Response({'error': '无法连接到 RAGflow 服务'}, status=503)
    except Exception as e:
        logger.error(f"安全知识库查询失败: {e}")
        return Response({'error': f'查询失败: {str(e)}'}, status=500)


# ── Locations ─────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def location_list(request):
    """返回启用的区域列表"""
    locations = Location.objects.filter(is_active=True)
    return Response(LocationSerializer(locations, many=True).data)


# ── Hazard Reports ────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def hazard_list_create(request):
    if request.method == 'GET':
        return _hazard_list(request)
    return _hazard_create(request)


def _hazard_list(request):
    qs = HazardReport.objects.select_related(
        'location', 'reporter', 'assignee'
    ).all()

    # Filters
    status_filter = request.query_params.get('status')
    level_filter = request.query_params.get('level')
    location_filter = request.query_params.get('location')
    reporter_filter = request.query_params.get('reporter')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    search = request.query_params.get('search', '').strip()

    if status_filter:
        qs = qs.filter(status=status_filter)
    if level_filter:
        qs = qs.filter(level=level_filter)
    if location_filter:
        qs = qs.filter(location_id=location_filter)
    if reporter_filter:
        qs = qs.filter(reporter_id=reporter_filter)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

    # Pagination
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    start = (page - 1) * page_size
    end = start + page_size
    total = qs.count()
    items = qs[start:end]

    serializer = HazardListSerializer(items, many=True, context={'request': request})
    return Response({
        'count': total,
        'page': page,
        'page_size': page_size,
        'results': serializer.data,
    })


def _hazard_create(request):
    serializer = HazardCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    hazard = serializer.save(reporter=request.user)

    # Handle uploaded images (field name: images, max 3)
    images = request.FILES.getlist('images')[:3]
    for img in images:
        HazardImage.objects.create(hazard=hazard, image=img, phase='report')

    # 同步创建统一整改工单
    severity = 'critical' if hazard.level == 'major' else 'general'
    location_text = hazard.location.name
    if hazard.location_detail:
        location_text = f'{location_text} {hazard.location_detail}'.strip()
    rect_svc.submit_issue(
        source=rect_svc.SourceRef(
            source_type='hazard_report',
            source_id=hazard.id,
            snapshot={
                'hazard_id': hazard.id,
                'level': hazard.level,
                'location_id': hazard.location_id,
                'location_detail': hazard.location_detail,
            },
        ),
        title=hazard.title,
        description=hazard.description,
        submitter=request.user,
        location_text=location_text,
        severity=severity,
        images=[img.image for img in hazard.images.filter(phase='report')],
    )

    logger.info(f"隐患上报: {hazard.title} by {request.user.username}")
    return Response(
        HazardDetailSerializer(hazard, context={'request': request}).data,
        status=status.HTTP_201_CREATED,
    )


def _get_linked_rect_order(hazard: HazardReport) -> RectificationOrder | None:
    """根据隐患反查关联的整改工单（最近一条）。"""
    return (
        RectificationOrder.objects
        .filter(source_type='hazard_report', source_id=hazard.id)
        .order_by('-created_at')
        .first()
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hazard_detail(request, pk):
    try:
        hazard = HazardReport.objects.select_related(
            'location', 'reporter', 'assignee', 'assigned_by', 'verified_by'
        ).prefetch_related('images').get(pk=pk)
    except HazardReport.DoesNotExist:
        return Response({'error': '隐患不存在'}, status=404)

    return Response(HazardDetailSerializer(hazard, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsSafetyOfficer])
def hazard_assign(request, pk):
    """安全员分派整改责任人"""
    try:
        hazard = HazardReport.objects.get(pk=pk)
    except HazardReport.DoesNotExist:
        return Response({'error': '隐患不存在'}, status=404)

    if hazard.status != 'pending':
        return Response({'error': '只有待分派状态的隐患可以分派'}, status=400)

    assignee_id = request.data.get('assignee_id')
    if not assignee_id:
        return Response({'error': '请选择整改责任人'}, status=400)

    from django.contrib.auth.models import User
    try:
        assignee = User.objects.get(pk=assignee_id)
    except User.DoesNotExist:
        return Response({'error': '用户不存在'}, status=400)

    hazard.assignee = assignee
    hazard.assigned_by = request.user
    hazard.assigned_at = timezone.now()
    hazard.status = 'fixing'
    hazard.save(update_fields=['assignee', 'assigned_by', 'assigned_at', 'status', 'updated_at'])

    # 同步关联整改工单
    order = _get_linked_rect_order(hazard)
    if order and order.status == 'pending':
        try:
            rect_svc.assign(order, assignee=assignee, assigner=request.user)
        except rect_svc.StateTransitionError as e:
            logger.warning('隐患 %s 关联工单分派失败: %s', hazard.id, e)

    logger.info(f"隐患分派: {hazard.title} -> {assignee.username}")
    return Response(HazardDetailSerializer(hazard, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def hazard_fix(request, pk):
    """整改责任人提交整改"""
    try:
        hazard = HazardReport.objects.get(pk=pk)
    except HazardReport.DoesNotExist:
        return Response({'error': '隐患不存在'}, status=404)

    if hazard.status not in ('fixing', 'rejected'):
        return Response({'error': '只有整改中或驳回状态的隐患可以提交整改'}, status=400)

    if hazard.assignee != request.user:
        return Response({'error': '只有整改责任人可以提交整改'}, status=403)

    fix_description = request.data.get('fix_description', '').strip()
    if not fix_description:
        return Response({'error': '请填写整改说明'}, status=400)

    hazard.fix_description = fix_description
    hazard.fixed_at = timezone.now()
    hazard.status = 'verifying'
    hazard.save(update_fields=['fix_description', 'fixed_at', 'status', 'updated_at'])

    # Optional fix images
    images = request.FILES.getlist('images')[:3]
    fix_images: list = []
    for img in images:
        obj = HazardImage.objects.create(hazard=hazard, image=img, phase='fix')
        fix_images.append(obj.image)

    # 同步关联整改工单
    order = _get_linked_rect_order(hazard)
    if order and order.status == 'fixing' and order.assignee_id == request.user.id:
        try:
            rect_svc.submit_rectification(
                order,
                operator=request.user,
                rectify_description=fix_description,
                images=fix_images,
            )
        except (rect_svc.StateTransitionError, PermissionError, ValueError) as e:
            logger.warning('隐患 %s 关联工单整改同步失败: %s', hazard.id, e)

    logger.info(f"隐患整改提交: {hazard.title} by {request.user.username}")
    return Response(HazardDetailSerializer(hazard, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsSafetyOfficer])
def hazard_verify(request, pk):
    """安全员验证整改结果"""
    try:
        hazard = HazardReport.objects.get(pk=pk)
    except HazardReport.DoesNotExist:
        return Response({'error': '隐患不存在'}, status=404)

    if hazard.status != 'verifying':
        return Response({'error': '只有待验证状态的隐患可以验证'}, status=400)

    action = request.data.get('action')
    remark = request.data.get('remark', '')

    if action == 'approve':
        hazard.status = 'closed'
    elif action == 'reject':
        hazard.status = 'rejected'
    else:
        return Response({'error': 'action 必须为 approve 或 reject'}, status=400)

    hazard.verified_by = request.user
    hazard.verified_at = timezone.now()
    hazard.verify_remark = remark
    hazard.save(update_fields=['verified_by', 'verified_at', 'verify_remark', 'status', 'updated_at'])

    # 同步关联整改工单
    order = _get_linked_rect_order(hazard)
    if order and order.status == 'verifying':
        try:
            rect_svc.verify(
                order,
                operator=request.user,
                passed=(action == 'approve'),
                remark=remark,
            )
        except (rect_svc.StateTransitionError, PermissionError) as e:
            logger.warning('隐患 %s 关联工单验证同步失败: %s', hazard.id, e)

    logger.info(f"隐患验证: {hazard.title} -> {action} by {request.user.username}")
    return Response(HazardDetailSerializer(hazard, context={'request': request}).data)


# ── 夹层施工管理 ──────────────────────────────────────────────────────────────

from .models import MezzanineRecord


def _mask_phone(phone: str) -> str:
    """脱敏手机号，保留前3位和后4位，中间4位替换为 ****
    例：13800138000 → 138****8000（phone[:3] + '****' + phone[7:]）
    """
    if len(phone) >= 8:
        return phone[:3] + '****' + phone[7:]
    return phone


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def mezzanine_checkin(request):
    """入场签到（公开接口，无需登录）"""
    name = request.data.get('name', '').strip()
    phone = request.data.get('phone', '').strip()
    company = request.data.get('company', '').strip()
    project = request.data.get('project', '').strip()
    count = int(request.data.get('count', 1))

    if not name:
        return Response({'error': '请填写姓名'}, status=400)
    if not phone:
        return Response({'error': '请填写手机号'}, status=400)
    if not project:
        return Response({'error': '请填写施工项目'}, status=400)
    if count < 1:
        return Response({'error': '人数至少为1'}, status=400)

    record = MezzanineRecord.objects.create(
        name=name, phone=phone, company=company, project=project, count=count
    )
    logger.info(f"夹层施工签到: {name} ({phone}) - {project}")
    return Response({
        'id': record.id,
        'name': record.name,
        'check_in_at': record.check_in_at.strftime('%Y-%m-%d %H:%M:%S'),
        'message': '签到成功',
    }, status=201)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def mezzanine_onsite(request):
    """当前在场人员列表（公开接口，手机号脱敏）"""
    records = MezzanineRecord.objects.filter(
        check_out_at__isnull=True
    ).order_by('check_in_at')
    data = [
        {
            'id': r.id,
            'name': r.name,
            'phone': _mask_phone(r.phone),
            'company': r.company,
            'project': r.project,
            'count': r.count,
            'check_in_at': r.check_in_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        for r in records
    ]
    return Response(data)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def mezzanine_checkout(request):
    """离场签退（公开接口，需验证手机号后四位）"""
    record_id = request.data.get('record_id')
    phone_last4 = request.data.get('phone_last4', '').strip()

    if not record_id:
        return Response({'error': '缺少 record_id'}, status=400)
    if not phone_last4 or len(phone_last4) != 4 or not phone_last4.isdigit():
        return Response({'error': '请输入手机号后四位（4位数字）'}, status=400)

    try:
        record = MezzanineRecord.objects.get(pk=record_id, check_out_at__isnull=True)
    except MezzanineRecord.DoesNotExist:
        return Response({'error': '记录不存在或已签退'}, status=404)

    if not record.phone.endswith(phone_last4):
        return Response({'error': '手机号后四位不匹配'}, status=400)

    record.check_out_at = timezone.now()
    record.save(update_fields=['check_out_at'])
    logger.info(f"夹层施工签退: {record.name} ({record.phone})")
    return Response({
        'name': record.name,
        'check_out_at': record.check_out_at.strftime('%Y-%m-%d %H:%M:%S'),
        'message': '签退成功',
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mezzanine_history(request):
    """历史记录查询（需登录，返回完整手机号）"""
    from django.db.models import Q
    from django.utils import timezone as tz

    qs = MezzanineRecord.objects.all()

    search = request.query_params.get('search', '').strip()
    project = request.query_params.get('project', '').strip()
    date_from = request.query_params.get('date_from', '').strip()
    date_to = request.query_params.get('date_to', '').strip()
    status_filter = request.query_params.get('status', '').strip()

    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(phone__icontains=search))
    if project:
        qs = qs.filter(project__icontains=project)
    if date_from:
        qs = qs.filter(check_in_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(check_in_at__date__lte=date_to)
    if status_filter == 'onsite':
        qs = qs.filter(check_out_at__isnull=True)
    elif status_filter == 'left':
        qs = qs.filter(check_out_at__isnull=False)

    # 手动分页，page_size 固定为 20（不接受客户端传入的 page_size 参数）
    page = int(request.query_params.get('page', 1))
    page_size = 20  # 硬编码，不从 query_params 读取
    total = qs.count()
    records = qs[(page - 1) * page_size: page * page_size]

    # 今日统计
    today = tz.localdate()
    from django.db.models import Sum

    today_count = MezzanineRecord.objects.filter(
        check_in_at__date=today
    ).aggregate(total=Sum('count'))['total'] or 0

    onsite_count = MezzanineRecord.objects.filter(
        check_out_at__isnull=True
    ).aggregate(total=Sum('count'))['total'] or 0

    def duration_str(r):
        end = r.check_out_at or tz.now()
        delta = end - r.check_in_at
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes = remainder // 60
        return f"{hours}h{minutes:02d}m"

    data = [
        {
            'id': r.id,
            'name': r.name,
            'phone': r.phone,
            'company': r.company,
            'project': r.project,
            'count': r.count,
            'check_in_at': r.check_in_at.strftime('%Y-%m-%d %H:%M:%S'),
            'check_out_at': r.check_out_at.strftime('%Y-%m-%d %H:%M:%S') if r.check_out_at else None,
            'duration': duration_str(r),
            'status': 'onsite' if r.check_out_at is None else 'left',
        }
        for r in records
    ]
    return Response({
        'count': total,
        'page': page,
        'results': data,
        'stats': {
            'today_count': today_count,
            'onsite_count': onsite_count,
        },
    })


@api_view(['POST'])
@permission_classes([IsSafetyOfficer])
def mezzanine_create(request):
    """管理员手动添加施工记录"""
    name = request.data.get('name', '').strip()
    phone = request.data.get('phone', '').strip()
    company = request.data.get('company', '').strip()
    project = request.data.get('project', '').strip()
    count = int(request.data.get('count', 1))

    if not name:
        return Response({'error': '请填写姓名'}, status=400)
    if not phone:
        return Response({'error': '请填写手机号'}, status=400)
    if not project:
        return Response({'error': '请填写施工项目'}, status=400)

    record = MezzanineRecord.objects.create(
        name=name, phone=phone, company=company, project=project, count=count
    )
    logger.info(f"夹层施工手动添加: {name} by {request.user.username}")
    return Response({
        'id': record.id,
        'name': record.name,
        'message': '添加成功',
    }, status=201)


@api_view(['PUT'])
@permission_classes([IsSafetyOfficer])
def mezzanine_update(request, pk):
    """管理员编辑施工记录"""
    try:
        record = MezzanineRecord.objects.get(pk=pk)
    except MezzanineRecord.DoesNotExist:
        return Response({'error': '记录不存在'}, status=404)

    name = request.data.get('name', '').strip()
    phone = request.data.get('phone', '').strip()
    company = request.data.get('company', '').strip()
    project = request.data.get('project', '').strip()
    count = int(request.data.get('count', record.count))

    if not name:
        return Response({'error': '请填写姓名'}, status=400)
    if not phone:
        return Response({'error': '请填写手机号'}, status=400)
    if not project:
        return Response({'error': '请填写施工项目'}, status=400)

    record.name = name
    record.phone = phone
    record.company = company
    record.project = project
    record.count = count
    record.save(update_fields=['name', 'phone', 'company', 'project', 'count'])

    logger.info(f"夹层施工编辑: {name} by {request.user.username}")
    return Response({'message': '更新成功'})


@api_view(['DELETE'])
@permission_classes([IsSafetyOfficer])
def mezzanine_delete(request, pk):
    """管理员删除施工记录"""
    try:
        record = MezzanineRecord.objects.get(pk=pk)
    except MezzanineRecord.DoesNotExist:
        return Response({'error': '记录不存在'}, status=404)

    logger.info(f"夹层施工删除: {record.name} by {request.user.username}")
    record.delete()
    return Response({'message': '删除成功'})
