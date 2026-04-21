import logging
from django.conf import settings
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)


def get_llm():
    """获取 Ollama LLM 实例"""
    return OllamaLLM(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
        temperature=0.3,
    )


REPAIR_PROMPT = PromptTemplate.from_template(
    """你是一位烟草制丝设备维修专家。请根据以下故障信息和参考资料，给出简洁、可操作的维修建议。

【故障信息】
设备：{equipment_name}（{equipment_code}）
位置：{location}
监控点：{point_name}（{param_type}）
当前值：{triggered_value} {unit}
报警类型：{alarm_level}
触发阈值：{threshold_value} {unit}

【知识库参考资料】
{rag_context}

请按以下格式回复：
1. 故障原因分析（2-3条可能原因）
2. 立即处置措施（按优先级排列）
3. 预防性维护建议"""
)


def build_repair_prompt(alarm) -> str:
    """根据报警记录构建维修建议 Prompt"""
    point = alarm.monitor_point
    equipment = point.equipment

    return REPAIR_PROMPT.format(
        equipment_name=equipment.name,
        equipment_code=equipment.code,
        location=equipment.location,
        point_name=point.name,
        param_type=point.get_param_type_display(),
        triggered_value=alarm.triggered_value,
        unit=point.unit,
        alarm_level=alarm.get_level_display(),
        threshold_value=alarm.threshold_value,
        rag_context="暂无相关资料",  # 占位，由 view 层替换
    )
