import json
import logging

from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.monitoring.models import AlarmRecord, RepairAdvice
from apps.monitoring.serializers import RepairAdviceSerializer
from apps.quality.analysis_service import (
    DEFAULT_TARGET_MOISTURE,
    DEFAULT_TOLERANCE,
    build_quality_summary,
    detect_moisture_anomalies,
)
from .ragflow_client import query_ragflow

logger = logging.getLogger(__name__)


def _load_langchain_client():
    from .langchain_client import REPAIR_PROMPT, get_llm

    return REPAIR_PROMPT, get_llm


def _build_quality_analysis_prompt(question, summary, anomalies):
    overview = summary['quality_overview']
    metrics = summary['metrics']['finished_moisture']
    standard = overview['standard']
    top_brands = ', '.join(
        f"{item['name']}({item['count']})" for item in summary['distributions']['brands'][:5]
    ) or '无'
    top_methods = ', '.join(
        f"{item['name']}({item['count']})" for item in summary['distributions']['addition_methods'][:5]
    ) or '无'
    anomaly_preview = '\n'.join(
        f"- 样品 {item['sample_number']} 风险分 {item['risk_score']}，原因：{'；'.join(item['reasons'])}"
        for item in anomalies['records'][:5]
    ) or '- 暂无明显异常'

    return f"""
你是一名烟草制丝质量分析师。请严格根据下列真实统计结果回答，不要虚构数据。

用户问题：{question or '请总结当前成品水分质量表现并指出风险'}

统计摘要：
- 记录数：{summary['scope']['total_records']}
- 品牌数：{summary['scope']['distinct_brands']}
- 当前默认标准：目标 {standard['target']}，容差 ±{standard['tolerance']}
- 成品水分均值：{metrics['avg']}
- 成品水分标准差：{metrics['std']}
- 成品水分最小值：{metrics['min']}
- 成品水分最大值：{metrics['max']}
- 成品水分达标率：{overview['finished_in_range_pct']}%
- 低于下限数量：{overview['finished_below_range_count']}
- 高于上限数量：{overview['finished_above_range_count']}
- 缺失取样日期数量：{overview['missing_sampling_date_count']}
- 缺失卷制水分数量：{overview['missing_rolling_moisture_count']}
- 常见品牌：{top_brands}
- 常见加丝方式：{top_methods}

异常样本预览：
{anomaly_preview}

请按以下格式回答：
1. 总体结论
2. 关键发现（不超过 3 条）
3. 建议动作（不超过 3 条）
""".strip()


def _fallback_quality_analysis(question, summary, anomalies):
    metrics = summary['metrics']['finished_moisture']
    overview = summary['quality_overview']
    anomaly_summary = anomalies['summary']
    standard = overview['standard']
    top_reason = anomalies['records'][0]['reasons'][0] if anomalies['records'] else '暂无明显异常'

    return '\n'.join(
        [
            f'总体结论：当前共分析 {summary["scope"]["total_records"]} 条记录，成品水分均值 {metrics["avg"]}，标准差 {metrics["std"]}，整体波动可继续收敛。',
            f'关键发现：当前默认判定标准为目标 {standard["target"]}、容差 ±{standard["tolerance"]}，若牌号已配置标准则自动按牌号判定。',
            f'关键发现：当前达标率约 {overview["finished_in_range_pct"]}%；低于下限 {overview["finished_below_range_count"]} 条，高于上限 {overview["finished_above_range_count"]} 条；高风险异常 {anomaly_summary["high_risk_count"]} 条。',
            f'关键发现：最突出的异常类型是“{top_reason}”，同时取样日期缺失 {overview["missing_sampling_date_count"]} 条，卷制水分缺失 {overview["missing_rolling_moisture_count"]} 条。',
            f'建议动作：围绕“{question or "总体质量表现"}”优先复盘高风险样本，并对重点牌号补充或校正目标值；默认可按 {DEFAULT_TARGET_MOISTURE}±{DEFAULT_TOLERANCE} 执行。',
        ]
    )


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def generate_repair_advice(request):
    alarm_id = request.data.get('alarm_id')
    if not alarm_id:
        return Response({'error': 'alarm_id is required'}, status=400)

    alarm = get_object_or_404(
        AlarmRecord.objects.select_related('monitor_point__equipment'),
        id=alarm_id,
    )

    try:
        existing = alarm.repair_advice
        return Response(RepairAdviceSerializer(existing).data)
    except RepairAdvice.DoesNotExist:
        pass

    point = alarm.monitor_point
    equipment = point.equipment
    question = f'{equipment.name} {point.name} {point.get_param_type_display()} 故障维修'
    rag_context = query_ragflow(question)
    repair_prompt, get_llm = _load_langchain_client()
    prompt_text = repair_prompt.format(
        equipment_name=equipment.name,
        equipment_code=equipment.code,
        location=equipment.location,
        point_name=point.name,
        param_type=point.get_param_type_display(),
        triggered_value=alarm.triggered_value,
        unit=point.unit,
        alarm_level=alarm.get_level_display(),
        threshold_value=alarm.threshold_value,
        rag_context=rag_context or '暂无相关资料',
    )

    llm = get_llm()
    full_response = []

    def event_stream():
        try:
            for chunk in llm.stream(prompt_text):
                full_response.append(chunk)
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            RepairAdvice.objects.update_or_create(
                alarm=alarm,
                defaults={'ai_response': ''.join(full_response), 'ragflow_context': rag_context},
            )
            yield 'data: [DONE]\n\n'
        except Exception as exc:
            logger.error('AI 生成维修建议失败: %s', exc)
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_repair_advice(request, alarm_id):
    advice = get_object_or_404(RepairAdvice, alarm_id=alarm_id)
    return Response(RepairAdviceSerializer(advice).data)


@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def quality_analysis_assistant(request):
    question = request.data.get('question', '').strip()
    brand_id = request.data.get('brand_id')
    brand_id = int(brand_id) if brand_id not in (None, '') else None

    summary = build_quality_summary(brand_id)
    anomalies = detect_moisture_anomalies(brand_id=brand_id, limit=10)
    prompt = _build_quality_analysis_prompt(question, summary, anomalies)

    try:
        _, get_llm = _load_langchain_client()
        llm = get_llm()
        answer = llm.invoke(prompt)
        source = 'llm'
    except Exception as exc:
        logger.warning('质量分析助手回退到规则摘要: %s', exc)
        answer = _fallback_quality_analysis(question, summary, anomalies)
        source = 'fallback'

    return Response(
        {
            'question': question,
            'answer': answer,
            'source': source,
            'summary': summary,
            'anomalies': anomalies,
        }
    )
