import json
import logging

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.monitoring.models import AlarmRecord, RepairAdvice
from apps.monitoring.serializers import RepairAdviceSerializer
from .langchain_client import get_llm, REPAIR_PROMPT
from .ragflow_client import query_ragflow

logger = logging.getLogger(__name__)


@api_view(['POST'])
def generate_repair_advice(request):
    """
    生成 AI 维修建议（SSE 流式响应）
    请求体：{"alarm_id": 1}
    """
    alarm_id = request.data.get('alarm_id')
    if not alarm_id:
        return Response({'error': 'alarm_id is required'}, status=400)

    alarm = get_object_or_404(
        AlarmRecord.objects.select_related('monitor_point__equipment'),
        id=alarm_id,
    )

    # 已有建议则直接返回
    try:
        existing = alarm.repair_advice
        return Response(RepairAdviceSerializer(existing).data)
    except RepairAdvice.DoesNotExist:
        pass

    # 1. 查询 RAGflow 知识库
    point = alarm.monitor_point
    equipment = point.equipment
    question = f"{equipment.name} {point.name} {point.get_param_type_display()} 故障维修"
    rag_context = query_ragflow(question)

    # 2. 组装 prompt
    prompt_text = REPAIR_PROMPT.format(
        equipment_name=equipment.name,
        equipment_code=equipment.code,
        location=equipment.location,
        point_name=point.name,
        param_type=point.get_param_type_display(),
        triggered_value=alarm.triggered_value,
        unit=point.unit,
        alarm_level=alarm.get_level_display(),
        threshold_value=alarm.threshold_value,
        rag_context=rag_context or "暂无相关资料",
    )

    # 3. 流式生成
    llm = get_llm()
    full_response = []

    def event_stream():
        try:
            for chunk in llm.stream(prompt_text):
                full_response.append(chunk)
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            # 存库
            RepairAdvice.objects.update_or_create(
                alarm=alarm,
                defaults={
                    'ai_response': ''.join(full_response),
                    'ragflow_context': rag_context,
                },
            )
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"AI 生成失败: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@api_view(['GET'])
def get_repair_advice(request, alarm_id):
    """获取已有维修建议"""
    advice = get_object_or_404(RepairAdvice, alarm_id=alarm_id)
    return Response(RepairAdviceSerializer(advice).data)
