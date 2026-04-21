import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def query_ragflow(question: str) -> str:
    """
    调用 RAGflow HTTP API 检索相关维修知识。
    未配置时返回空字符串，LLM 凭自身知识回答。
    """
    if not settings.RAGFLOW_API_KEY or not settings.RAGFLOW_BASE_URL:
        logger.info("RAGflow 未配置，跳过知识库检索")
        return ""

    url = f"{settings.RAGFLOW_BASE_URL}/api/v1/retrieval"
    headers = {
        "Authorization": f"Bearer {settings.RAGFLOW_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "question": question,
        "dataset_ids": [settings.RAGFLOW_DATASET_ID],
        "top_n": 3,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        chunks = resp.json().get('data', {}).get('chunks', [])
        context = "\n\n".join(c.get('content', '') for c in chunks)
        logger.info(f"RAGflow 返回 {len(chunks)} 条结果")
        return context
    except Exception as e:
        logger.warning(f"RAGflow 查询失败: {e}")
        return ""
