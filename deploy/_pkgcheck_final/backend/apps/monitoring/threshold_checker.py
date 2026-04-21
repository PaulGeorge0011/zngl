import logging
from typing import Optional
from .models import ThresholdRule, AlarmRecord, SensorReading

logger = logging.getLogger(__name__)


def check_thresholds(reading: SensorReading) -> Optional[AlarmRecord]:
    """
    检查单条读数是否触发阈值。
    返回新建的 AlarmRecord 或 None。
    规则优先级：alarm > warning，上限优先于下限。
    防抖：同一监控点已有同级 active 报警时不重复创建。
    """
    try:
        rule = reading.monitor_point.threshold
    except ThresholdRule.DoesNotExist:
        return None

    if not rule.is_active:
        return None

    value = reading.value
    level = None
    threshold_value = None

    # 按优先级检查：报警 > 预警
    if rule.alarm_high is not None and value > rule.alarm_high:
        level, threshold_value = 'alarm', rule.alarm_high
    elif rule.alarm_low is not None and value < rule.alarm_low:
        level, threshold_value = 'alarm', rule.alarm_low
    elif rule.warning_high is not None and value > rule.warning_high:
        level, threshold_value = 'warning', rule.warning_high
    elif rule.warning_low is not None and value < rule.warning_low:
        level, threshold_value = 'warning', rule.warning_low

    if level is None:
        return None

    # 防抖：已有同级未处理报警则跳过
    exists = AlarmRecord.objects.filter(
        monitor_point=reading.monitor_point,
        level=level,
        status='active',
    ).exists()
    if exists:
        return None

    alarm = AlarmRecord.objects.create(
        monitor_point=reading.monitor_point,
        level=level,
        triggered_value=value,
        threshold_value=threshold_value,
    )
    logger.info(
        f"报警触发: {reading.monitor_point} {level} "
        f"value={value} threshold={threshold_value}"
    )

    # 通过 WebSocket 推送
    _push_alarm_to_ws(alarm)
    return alarm


def _push_alarm_to_ws(alarm: AlarmRecord):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        async_to_sync(channel_layer.group_send)(
            'monitoring',
            {
                'type': 'alarm.triggered',
                'data': {
                    'id': alarm.id,
                    'level': alarm.level,
                    'status': alarm.status,
                    'triggered_value': alarm.triggered_value,
                    'threshold_value': alarm.threshold_value,
                    'monitor_point_id': alarm.monitor_point_id,
                    'equipment_name': alarm.monitor_point.equipment.name,
                    'point_name': alarm.monitor_point.name,
                    'unit': alarm.monitor_point.unit,
                    'triggered_at': alarm.triggered_at.isoformat(),
                },
            },
        )
    except Exception as e:
        logger.warning(f"WebSocket 推送报警失败: {e}")
