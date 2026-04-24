"""短信通知封装 (仅 safety 模块内部使用)

- 配置见 settings.base 的 SMS_* 环境变量
- 所有调用均为 best-effort：失败只记录日志，不抛异常、不阻塞业务
- 使用后台线程发送，避免 API 响应被外部短信接口拖慢
"""
import logging
import threading
from datetime import datetime
from typing import Iterable, Optional

import requests
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


def _get_config():
    return {
        'enabled': getattr(settings, 'SMS_ENABLED', False),
        'url': getattr(settings, 'SMS_API_URL', ''),
        'system': getattr(settings, 'SMS_SYSTEM_NAME', '数智生产'),
        'timeout': getattr(settings, 'SMS_TIMEOUT', 8),
    }


def _do_send(phones: list, content: str) -> bool:
    cfg = _get_config()
    if not cfg['enabled']:
        logger.info('[SMS] disabled by settings, skip. phones=%s', phones)
        return False
    if not cfg['url']:
        logger.warning('[SMS] SMS_API_URL empty, skip.')
        return False
    if not phones:
        logger.info('[SMS] empty phone list, skip.')
        return False

    payload = {
        'userList': phones,
        'content': content,
        'system': cfg['system'],
    }
    try:
        resp = requests.post(
            cfg['url'],
            json=payload,
            timeout=cfg['timeout'],
        )
        ok = resp.status_code == 200
        logger.info(
            '[SMS] sent phones=%s status=%s resp=%s',
            phones, resp.status_code, resp.text[:200],
        )
        return ok
    except Exception as e:
        logger.exception('[SMS] send failed phones=%s err=%s', phones, e)
        return False


def send_sms_async(phones: Iterable[str], content: str, on_success=None) -> None:
    """后台线程发送，on_success 可选回调 (仅成功时调用)"""
    phones = [p for p in phones if p]
    if not phones:
        logger.info('[SMS] no valid phone, skip.')
        return

    def _worker():
        ok = _do_send(phones, content)
        if ok and on_success:
            try:
                on_success()
            except Exception:
                logger.exception('[SMS] on_success callback failed')

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def build_duty_reminder(duty_date) -> str:
    """按用户要求的模板生成短信内容"""
    if hasattr(duty_date, 'strftime'):
        date_text = duty_date.strftime('%Y年%m月%d日')
    else:
        try:
            dt = datetime.strptime(str(duty_date), '%Y-%m-%d')
            date_text = dt.strftime('%Y年%m月%d日')
        except Exception:
            date_text = str(duty_date)
    return (
        f'[制丝二智能管理中枢] 您负责的夜班监督检查将在{date_text}进行，'
        f'请登录云中玉烟-制二综合管理-智能管理中枢，查看详情，'
        f'如需变更监护时间请与管理员联系，谢谢！'
    )


# ── 整改中心相关 ──────────────────────────────────────────────────────────────

_RECT_FOOTER = '详情请登录新媒体云中玉烟-制二综合管理-智能管理中枢-整改中心，进行查看。'


def _user_phone(user) -> str:
    """从 UserProfile 取手机号；空则返回空串。"""
    if not user:
        return ''
    profile = getattr(user, 'profile', None)
    if not profile:
        return ''
    phone = getattr(profile, 'phone', '') or ''
    return phone.strip()


def _fmt_deadline(dt) -> str:
    """期限格式化：2026年04月24日18时30分。"""
    if not dt:
        return '指定时间'
    return timezone.localtime(dt).strftime('%Y年%m月%d日%H时%M分')


def _fmt_now_dt() -> str:
    return timezone.localtime(timezone.now()).strftime('%Y年%m月%d日%H时%M分')


def build_rect_assigned_content(role: str, deadline) -> str:
    """分派整改责任人 / 分派验证人 的短信模板。

    role: '负责' 或 '验证'
    """
    return (
        f'[制丝二智能管理中枢]您{role}的问题整改将在'
        f'{_fmt_deadline(deadline)}截止，'
        f'{_RECT_FOOTER}'
    )


def build_rect_closed_content() -> str:
    """工单闭环通知提交人的短信模板。"""
    return (
        f'[制丝二智能管理中枢]您提交的问题已于在'
        f'{_fmt_now_dt()}完成闭环整改，'
        f'{_RECT_FOOTER}'
    )


def build_rect_created_content(source_display: str, title: str) -> str:
    """整改中心新工单的通知模板（给配置的关注人）。"""
    return (
        f'[制丝二智能管理中枢]整改中心新增[{source_display}]问题：'
        f'{title}，{_RECT_FOOTER}'
    )


def notify_rect_assigned(order) -> None:
    """分派整改责任人后通知：assignee -> 负责。"""
    phone = _user_phone(order.assignee)
    if not phone:
        logger.info('[SMS] rect %s assignee no phone, skip', order.id)
        return
    content = build_rect_assigned_content('负责', order.deadline)
    send_sms_async([phone], content)


def notify_rect_verifier_assigned(order) -> None:
    """分派验证人后通知：verifier -> 验证。"""
    phone = _user_phone(order.verifier)
    if not phone:
        logger.info('[SMS] rect %s verifier no phone, skip', order.id)
        return
    content = build_rect_assigned_content('验证', order.deadline)
    send_sms_async([phone], content)


def notify_rect_closed(order) -> None:
    """工单验证通过闭环后通知提交人。"""
    phone = _user_phone(order.submitter)
    if not phone:
        logger.info('[SMS] rect %s submitter no phone, skip', order.id)
        return
    content = build_rect_closed_content()
    send_sms_async([phone], content)


def notify_rect_created(order) -> None:
    """新工单创建后，通知配置表里匹配来源的接收人。"""
    from .models import RectificationNotifyRecipient

    recipients = RectificationNotifyRecipient.objects.filter(enabled=True).filter(
        Q(source_type='') | Q(source_type=order.source_type)
    ).select_related('user__profile')

    phones = []
    for r in recipients:
        phone = _user_phone(r.user)
        if phone and phone not in phones:
            phones.append(phone)
    if not phones:
        logger.info('[SMS] rect %s no configured recipients, skip', order.id)
        return

    content = build_rect_created_content(order.get_source_type_display(), order.title)
    send_sms_async(phones, content)


def notify_duty_assigned(duty) -> Optional[bool]:
    """
    给排班 duty 对应的检查人发送提醒短信。
    成功发送后自动更新 duty.sms_sent_at。

    返回：
      - None 表示未发（无手机号 / 未启用 / 已发送过同一天）
      - True / False 由异步线程决定 (这里总是返回 None，真实结果看日志)
    """
    if not duty or not duty.inspector_id:
        return None

    user = duty.inspector
    phone = ''
    profile = getattr(user, 'profile', None)
    if profile and getattr(profile, 'phone', ''):
        phone = profile.phone.strip()

    if not phone:
        logger.info('[SMS] inspector %s has no phone, skip duty %s',
                    user.username if user else '?', duty.pk)
        return None

    content = build_duty_reminder(duty.duty_date)
    duty_pk = duty.pk

    def _mark_sent():
        from .models import NightShiftDuty
        NightShiftDuty.objects.filter(pk=duty_pk).update(sms_sent_at=timezone.now())

    send_sms_async([phone], content, on_success=_mark_sent)
    return None
