import json
import logging
from datetime import timedelta

from django.utils import timezone
from django.db.models import Max
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from apps.equipment.models import MonitorPoint
from .models import ThresholdRule, SensorReading, AlarmRecord
from .serializers import (
    ThresholdRuleSerializer,
    SensorReadingSerializer,
    AlarmRecordSerializer,
)
from .threshold_checker import check_thresholds

logger = logging.getLogger(__name__)


class ThresholdRuleViewSet(viewsets.ModelViewSet):
    queryset = ThresholdRule.objects.select_related('monitor_point').all()
    serializer_class = ThresholdRuleSerializer
    permission_classes = [AllowAny]


@api_view(['POST'])
@permission_classes([AllowAny])
def receive_readings(request):
    """接收传感器数据（支持批量）"""
    readings_data = request.data.get('readings', [])
    if not readings_data:
        # 兼容单条数据
        readings_data = [request.data]

    created = []
    alarms_triggered = []

    for item in readings_data:
        serializer = SensorReadingSerializer(data=item)
        if serializer.is_valid():
            reading = serializer.save()
            created.append(reading)
            # 检查阈值
            alarm = check_thresholds(reading)
            if alarm:
                alarms_triggered.append(alarm.id)
            # WebSocket 推送传感器数据
            _push_sensor_to_ws(reading)
        else:
            logger.warning(f"无效数据: {serializer.errors}")

    return Response({
        'created': len(created),
        'alarms_triggered': alarms_triggered,
    }, status=status.HTTP_201_CREATED)


def _push_sensor_to_ws(reading: SensorReading):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        async_to_sync(channel_layer.group_send)(
            'monitoring',
            {
                'type': 'sensor.update',
                'data': {
                    'monitor_point_id': reading.monitor_point_id,
                    'equipment_id': reading.monitor_point.equipment_id,
                    'value': reading.value,
                    'recorded_at': reading.recorded_at.isoformat(),
                    'point_name': reading.monitor_point.name,
                    'unit': reading.monitor_point.unit,
                    'param_type': reading.monitor_point.param_type,
                },
            },
        )
    except Exception as e:
        logger.warning(f"WebSocket 推送传感器数据失败: {e}")


@api_view(['GET'])
@permission_classes([AllowAny])
def get_readings_history(request):
    """查询历史数据（用于绘图）"""
    point_id = request.query_params.get('point_id')
    minutes = int(request.query_params.get('minutes', 60))

    if not point_id:
        return Response({'error': 'point_id is required'}, status=400)

    since = timezone.now() - timedelta(minutes=minutes)
    readings = SensorReading.objects.filter(
        monitor_point_id=point_id,
        recorded_at__gte=since,
    ).order_by('recorded_at')

    serializer = SensorReadingSerializer(readings, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_latest_readings(request):
    """获取某设备所有监控点的最新值"""
    equipment_id = request.query_params.get('equipment_id')
    if not equipment_id:
        return Response({'error': 'equipment_id is required'}, status=400)

    points = MonitorPoint.objects.filter(equipment_id=equipment_id)
    result = []

    for point in points:
        latest = SensorReading.objects.filter(monitor_point=point).first()
        threshold = getattr(point, 'threshold', None)
        result.append({
            'monitor_point_id': point.id,
            'name': point.name,
            'param_key': point.param_key,
            'param_type': point.param_type,
            'unit': point.unit,
            'value': latest.value if latest else None,
            'recorded_at': latest.recorded_at.isoformat() if latest else None,
            'threshold': {
                'warning_high': threshold.warning_high if threshold else None,
                'warning_low': threshold.warning_low if threshold else None,
                'alarm_high': threshold.alarm_high if threshold else None,
                'alarm_low': threshold.alarm_low if threshold else None,
            } if threshold else None,
        })

    return Response(result)


class AlarmRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AlarmRecord.objects.select_related(
        'monitor_point__equipment'
    ).all()
    permission_classes = [AllowAny]
    serializer_class = AlarmRecordSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'level', 'monitor_point__equipment']

    @action(detail=True, methods=['patch'])
    def acknowledge(self, request, pk=None):
        alarm = self.get_object()
        if alarm.status != 'active':
            return Response({'error': '只能确认未处理的报警'}, status=400)
        alarm.status = 'acknowledged'
        alarm.save(update_fields=['status'])
        return Response(AlarmRecordSerializer(alarm).data)

    @action(detail=True, methods=['patch'])
    def resolve(self, request, pk=None):
        alarm = self.get_object()
        if alarm.status == 'resolved':
            return Response({'error': '报警已解决'}, status=400)
        alarm.status = 'resolved'
        alarm.resolved_at = timezone.now()
        alarm.note = request.data.get('note', '')
        alarm.save(update_fields=['status', 'resolved_at', 'note'])
        return Response(AlarmRecordSerializer(alarm).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def dashboard_stats(request):
    """Dashboard 统计数据"""
    from apps.equipment.models import Equipment

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    return Response({
        'equipment_total': Equipment.objects.count(),
        'equipment_running': Equipment.objects.filter(status='running').count(),
        'equipment_fault': Equipment.objects.filter(status='fault').count(),
        'alarms_active': AlarmRecord.objects.filter(status='active').count(),
        'alarms_today': AlarmRecord.objects.filter(triggered_at__gte=today_start).count(),
        'readings_today': SensorReading.objects.filter(recorded_at__gte=today_start).count(),
    })
