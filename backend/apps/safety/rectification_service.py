"""整改工单领域服务。

所有状态流转都必须经过此模块，以保证状态机一致性和审计日志完整。
业务模块（隐患、除尘房巡检、夜班监护）通过 ``submit_issue`` 统一提交问题。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Iterable, Optional

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from . import sms
from .models import RectificationOrder, RectificationImage, RectificationLog

logger = logging.getLogger(__name__)


# 默认整改期限（按严重等级）——分派时若未手动指定，按此计算。
DEFAULT_DEADLINE_DAYS = {
    'general': 7,
    'major': 3,
    'critical': 1,
}


@dataclass(frozen=True)
class SourceRef:
    """整改来源引用 — 业务模块构造此对象提交问题。"""

    source_type: str
    source_id: int
    snapshot: dict = field(default_factory=dict)


class StateTransitionError(ValueError):
    """状态机非法转换。"""


def default_deadline(severity: str, base: Optional[datetime] = None) -> datetime:
    base = base or timezone.now()
    days = DEFAULT_DEADLINE_DAYS.get(severity, DEFAULT_DEADLINE_DAYS['general'])
    return base + timedelta(days=days)


@transaction.atomic
def submit_issue(
    *,
    source: SourceRef,
    title: str,
    description: str,
    submitter: User,
    location_text: str = '',
    severity: str = 'general',
    images: Optional[Iterable[Any]] = None,
) -> RectificationOrder:
    """业务模块统一调用此方法下发整改工单。"""
    order = RectificationOrder.objects.create(
        source_type=source.source_type,
        source_id=source.source_id,
        source_snapshot=source.snapshot or {},
        title=title,
        description=description,
        location_text=location_text,
        severity=severity,
        submitter=submitter,
        status='pending',
    )
    RectificationLog.objects.create(
        order=order,
        action='create',
        operator=submitter,
        from_status='',
        to_status='pending',
        remark=f'来源 {source.source_type}:{source.source_id}',
    )
    if images:
        for img in list(images)[:3]:
            RectificationImage.objects.create(order=order, image=img, phase='issue')
    logger.info(
        '整改工单创建: id=%s source=%s:%s by %s',
        order.id, source.source_type, source.source_id, submitter.username,
    )

    # 通知场景(1): 新工单 -> 给配置接收人群发
    try:
        sms.notify_rect_created(order)
    except Exception:
        logger.exception('notify_rect_created failed for order %s', order.id)

    return order


@transaction.atomic
def assign(
    order: RectificationOrder,
    *,
    assignee: User,
    assigner: User,
    deadline: Optional[datetime] = None,
    remark: str = '',
) -> RectificationOrder:
    """分派整改责任人；待分派 → 整改中。"""
    if order.status != 'pending':
        raise StateTransitionError('只有待分派状态的工单可以分派')

    prev = order.status
    order.assignee = assignee
    order.assigner = assigner
    order.assigned_at = timezone.now()
    order.deadline = deadline or default_deadline(order.severity)
    order.status = 'fixing'
    order.save(update_fields=[
        'assignee', 'assigner', 'assigned_at', 'deadline', 'status', 'updated_at',
    ])

    RectificationLog.objects.create(
        order=order,
        action='assign',
        operator=assigner,
        from_status=prev,
        to_status='fixing',
        remark=remark or f'分派给 {assignee.username}, 期限 {order.deadline:%Y-%m-%d %H:%M}',
    )

    # 通知场景(2): 分派整改责任人 -> 通知 assignee
    try:
        sms.notify_rect_assigned(order)
    except Exception:
        logger.exception('notify_rect_assigned failed for order %s', order.id)

    return order


@transaction.atomic
def assign_verifier(
    order: RectificationOrder,
    *,
    verifier: User,
    operator: User,
    remark: str = '',
) -> RectificationOrder:
    """分派验证责任人。任意尚未闭环/取消的工单都可被指派或改派验证人。"""
    if order.status in ('closed', 'cancelled'):
        raise StateTransitionError('已闭环/已取消的工单不能指派验证人')
    if order.assignee_id and order.assignee_id == verifier.id:
        raise ValueError('验证人不能是整改责任人')

    prev_verifier = order.verifier
    order.verifier = verifier
    order.verifier_assigner = operator
    order.verifier_assigned_at = timezone.now()
    order.save(update_fields=[
        'verifier', 'verifier_assigner', 'verifier_assigned_at', 'updated_at',
    ])

    action_remark = remark or (
        f'指派验证人: {verifier.username}' if prev_verifier is None
        else f'改派验证人: {prev_verifier.username} -> {verifier.username}'
    )
    RectificationLog.objects.create(
        order=order,
        action='assign_verifier',
        operator=operator,
        from_status=order.status,
        to_status=order.status,
        remark=action_remark,
    )

    # 通知场景(3): 分派验证人 -> 通知 verifier
    try:
        sms.notify_rect_verifier_assigned(order)
    except Exception:
        logger.exception('notify_rect_verifier_assigned failed for order %s', order.id)

    return order


@transaction.atomic
def reassign(
    order: RectificationOrder,
    *,
    assignee: User,
    operator: User,
    deadline: Optional[datetime] = None,
    remark: str = '',
) -> RectificationOrder:
    """改派：整改中/待验证状态下允许更换整改人。"""
    if order.status not in ('fixing', 'verifying'):
        raise StateTransitionError('只有整改中/待验证状态可以改派')

    prev_assignee = order.assignee
    order.assignee = assignee
    if deadline:
        order.deadline = deadline
    # 若原状态是待验证，改派意味着要重新整改，回到整改中
    prev_status = order.status
    if order.status == 'verifying':
        order.status = 'fixing'
    order.save(update_fields=['assignee', 'deadline', 'status', 'updated_at'])

    RectificationLog.objects.create(
        order=order,
        action='reassign',
        operator=operator,
        from_status=prev_status,
        to_status=order.status,
        remark=remark or f'从 {prev_assignee} 改派至 {assignee.username}',
    )
    return order


@transaction.atomic
def submit_rectification(
    order: RectificationOrder,
    *,
    operator: User,
    rectify_description: str,
    images: Optional[Iterable[Any]] = None,
) -> RectificationOrder:
    """整改责任人提交整改；整改中 → 待验证。"""
    if order.status != 'fixing':
        raise StateTransitionError('只有整改中状态的工单可以提交整改')
    if order.assignee_id != operator.id:
        raise PermissionError('只有整改责任人可以提交整改')
    if not rectify_description.strip():
        raise ValueError('整改说明不能为空')

    prev = order.status
    order.rectify_description = rectify_description.strip()
    order.rectified_at = timezone.now()
    order.status = 'verifying'
    order.save(update_fields=[
        'rectify_description', 'rectified_at', 'status', 'updated_at',
    ])

    if images:
        for img in list(images)[:3]:
            RectificationImage.objects.create(order=order, image=img, phase='rectify')

    RectificationLog.objects.create(
        order=order,
        action='submit_rectify',
        operator=operator,
        from_status=prev,
        to_status='verifying',
    )
    return order


@transaction.atomic
def verify(
    order: RectificationOrder,
    *,
    operator: User,
    passed: bool,
    remark: str = '',
) -> RectificationOrder:
    """验证整改结果；待验证 → 已闭环 / 整改中（驳回）。"""
    if order.status != 'verifying':
        raise StateTransitionError('只有待验证状态的工单可以验证')
    if order.assignee_id == operator.id:
        raise PermissionError('不能验证自己整改的工单')

    prev = order.status
    # 若工单已预分派验证人，保留原指派；否则把 operator 作为本次验证人
    if not order.verifier_id:
        order.verifier = operator
    order.verified_at = timezone.now()
    order.verify_remark = remark or ''
    order.status = 'closed' if passed else 'fixing'
    update_fields = ['verifier', 'verified_at', 'verify_remark', 'status', 'updated_at']
    if not passed:
        order.reject_count = (order.reject_count or 0) + 1
        order.rectified_at = None  # 清空上一次整改时间，让责任人重新提交
        update_fields.extend(['reject_count', 'rectified_at'])
    order.save(update_fields=update_fields)

    RectificationLog.objects.create(
        order=order,
        action='verify_pass' if passed else 'verify_reject',
        operator=operator,
        from_status=prev,
        to_status=order.status,
        remark=remark,
    )

    # 通知场景(4): 工单闭环 -> 通知 submitter
    if passed:
        try:
            sms.notify_rect_closed(order)
        except Exception:
            logger.exception('notify_rect_closed failed for order %s', order.id)

    return order


@transaction.atomic
def cancel(
    order: RectificationOrder,
    *,
    operator: User,
    remark: str,
) -> RectificationOrder:
    """取消工单（误报/重复）；仅允许在未闭环前操作。"""
    if order.status == 'closed':
        raise StateTransitionError('已闭环的工单无法取消')
    if not remark.strip():
        raise ValueError('取消工单必须填写原因')

    prev = order.status
    order.status = 'cancelled'
    order.save(update_fields=['status', 'updated_at'])

    RectificationLog.objects.create(
        order=order,
        action='cancel',
        operator=operator,
        from_status=prev,
        to_status='cancelled',
        remark=remark.strip(),
    )
    return order


def mark_overdue() -> int:
    """扫描并标记逾期工单。由 management command / 定时任务调用。"""
    now = timezone.now()
    qs = RectificationOrder.objects.filter(
        status__in=['pending', 'fixing'],
        deadline__lt=now,
        overdue=False,
    )
    count = 0
    for order in qs:
        order.overdue = True
        order.save(update_fields=['overdue'])
        RectificationLog.objects.create(
            order=order,
            action='auto_overdue',
            operator=None,
            from_status=order.status,
            to_status=order.status,
            remark=f'已逾期 {now - order.deadline}',
        )
        count += 1
    if count:
        logger.info('标记逾期整改工单: %d 条', count)
    return count
