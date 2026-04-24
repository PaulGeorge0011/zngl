from django.db import models
from django.contrib.auth.models import User


class Location(models.Model):
    """可配置的车间区域"""
    name = models.CharField('区域名称', max_length=50, unique=True)
    sort_order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('启用', default=True)

    class Meta:
        verbose_name = '区域'
        verbose_name_plural = '区域'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class HazardReport(models.Model):
    """安全隐患上报"""

    LEVEL_CHOICES = [
        ('general', '一般隐患'),
        ('major', '重大隐患'),
    ]
    STATUS_CHOICES = [
        ('pending', '待分派'),
        ('fixing', '整改中'),
        ('verifying', '待验证'),
        ('closed', '已关闭'),
        ('rejected', '驳回'),
    ]

    title = models.CharField('标题', max_length=100)
    description = models.TextField('描述')
    level = models.CharField('等级', max_length=10, choices=LEVEL_CHOICES)
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, verbose_name='区域'
    )
    location_detail = models.CharField('具体位置', max_length=200, blank=True)
    status = models.CharField(
        '状态', max_length=20, choices=STATUS_CHOICES, default='pending'
    )

    # 上报
    reporter = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='reported_hazards', verbose_name='上报人'
    )

    # 分派
    assignee = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_hazards', verbose_name='整改责任人'
    )
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dispatched_hazards', verbose_name='分派人'
    )
    assigned_at = models.DateTimeField('分派时间', null=True, blank=True)

    # 整改
    fix_description = models.TextField('整改说明', blank=True)
    fixed_at = models.DateTimeField('整改完成时间', null=True, blank=True)

    # 验证
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verified_hazards', verbose_name='验证人'
    )
    verified_at = models.DateTimeField('验证时间', null=True, blank=True)
    verify_remark = models.TextField('验证备注', blank=True)

    created_at = models.DateTimeField('上报时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '隐患上报'
        verbose_name_plural = '隐患上报'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_level_display()}] {self.title}"


class HazardImage(models.Model):
    """隐患图片"""

    PHASE_CHOICES = [
        ('report', '上报'),
        ('fix', '整改'),
    ]

    hazard = models.ForeignKey(
        HazardReport, on_delete=models.CASCADE,
        related_name='images', verbose_name='隐患'
    )
    image = models.ImageField('图片', upload_to='hazards/%Y/%m/')
    phase = models.CharField('阶段', max_length=10, choices=PHASE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '隐患图片'
        verbose_name_plural = '隐患图片'


INSPECTION_ROLE_CHOICES = [
    ('electrical', '电气修理工'),
    ('mechanical', '机械修理工'),
    ('operator', '操作工'),
    ('safety', '安全员'),
]

FREQUENCY_CHOICES = [
    ('daily', '每天'),
    ('per_shift', '每班次'),
    ('weekly', '每周'),
    ('monthly', '每月'),
]

ITEM_TYPE_CHOICES = [
    ('checkbox', '正常/异常'),
    ('number', '数值'),
    ('text', '文本'),
    ('select', '选择'),
]


class DustRoom(models.Model):
    """除尘房"""
    name = models.CharField('名称', max_length=50, unique=True)
    code = models.CharField('编号', max_length=20, unique=True)
    description = models.TextField('描述', blank=True)
    is_active = models.BooleanField('启用', default=True)
    sort_order = models.IntegerField('排序', default=0)

    class Meta:
        verbose_name = '除尘房'
        verbose_name_plural = '除尘房'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class InspectionTemplate(models.Model):
    """巡检模板（每种角色一个）"""
    role = models.CharField('巡检角色', max_length=20, choices=INSPECTION_ROLE_CHOICES, unique=True)
    name = models.CharField('模板名称', max_length=100)
    frequency = models.CharField('巡检频次', max_length=20, choices=FREQUENCY_CHOICES, default='daily')
    is_active = models.BooleanField('启用', default=True)

    class Meta:
        verbose_name = '巡检模板'
        verbose_name_plural = '巡检模板'

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"


class InspectionItem(models.Model):
    """巡检检查项"""
    template = models.ForeignKey(
        InspectionTemplate, on_delete=models.CASCADE,
        related_name='items', verbose_name='所属模板',
    )
    name = models.CharField('检查项名称', max_length=200)
    item_type = models.CharField('类型', max_length=20, choices=ITEM_TYPE_CHOICES, default='checkbox')
    options = models.JSONField('选项列表', default=list, blank=True,
                               help_text='select 类型时填写，如 ["好","中","差"]')
    unit = models.CharField('单位', max_length=50, blank=True, help_text='number 类型时填写，如 ℃')
    required = models.BooleanField('必填', default=True)
    sort_order = models.IntegerField('排序', default=0)

    class Meta:
        verbose_name = '巡检检查项'
        verbose_name_plural = '巡检检查项'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.template.get_role_display()} - {self.name}"


class DustRoomInspector(models.Model):
    """除尘房巡检人员分配"""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='dustroom_roles', verbose_name='用户',
    )
    role = models.CharField('巡检角色', max_length=20, choices=INSPECTION_ROLE_CHOICES)

    class Meta:
        verbose_name = '除尘房巡检人员'
        verbose_name_plural = '除尘房巡检人员'
        unique_together = ['user', 'role']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_role_display()}"


class InspectionRecord(models.Model):
    """巡检记录"""
    STATUS_CHOICES = [
        ('in_progress', '进行中'),
        ('submitted', '已提交'),
    ]

    dust_room = models.ForeignKey(
        DustRoom, on_delete=models.PROTECT,
        related_name='inspection_records', verbose_name='除尘房',
    )
    template = models.ForeignKey(
        InspectionTemplate, on_delete=models.PROTECT, verbose_name='巡检模板',
    )
    inspector = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='inspection_records', verbose_name='巡检人',
    )
    inspection_date = models.DateField('巡检日期')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='in_progress')
    has_abnormal = models.BooleanField('存在异常', default=False)
    remark = models.TextField('备注', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    submitted_at = models.DateTimeField('提交时间', null=True, blank=True)

    class Meta:
        verbose_name = '巡检记录'
        verbose_name_plural = '巡检记录'
        ordering = ['-inspection_date', '-created_at']

    def __str__(self):
        return f"{self.dust_room.name} - {self.template.get_role_display()} - {self.inspection_date}"


class InspectionItemResult(models.Model):
    """巡检检查项结果"""
    record = models.ForeignKey(
        InspectionRecord, on_delete=models.CASCADE,
        related_name='results', verbose_name='巡检记录',
    )
    item = models.ForeignKey(
        InspectionItem, on_delete=models.PROTECT, verbose_name='检查项',
    )
    value = models.TextField('填写值', blank=True)
    is_normal = models.BooleanField('是否正常', default=True)
    remark = models.TextField('异常备注', blank=True)

    class Meta:
        verbose_name = '检查项结果'
        verbose_name_plural = '检查项结果'

    def __str__(self):
        status = '正常' if self.is_normal else '异常'
        return f"{self.item.name}: {status}"


# ── 夜班监护检查 ─────────────────────────────────────────────────────────────

class NightShiftCategory(models.Model):
    """夜班监护检查分类（作业行为/工器具/重点检查部位）"""
    name = models.CharField('分类名称', max_length=50, unique=True)
    allows_custom = models.BooleanField('允许自填项', default=False,
                                        help_text='重点检查部位允许巡检人员自行添加检查条目')
    sort_order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('启用', default=True)

    class Meta:
        verbose_name = '夜班检查分类'
        verbose_name_plural = '夜班检查分类'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.name


class NightShiftCheckItem(models.Model):
    """夜班监护检查预置项"""
    category = models.ForeignKey(
        NightShiftCategory, on_delete=models.CASCADE,
        related_name='items', verbose_name='所属分类',
    )
    name = models.CharField('检查项名称', max_length=200)
    is_active = models.BooleanField('启用', default=True)
    sort_order = models.IntegerField('排序', default=0)

    class Meta:
        verbose_name = '夜班检查预置项'
        verbose_name_plural = '夜班检查预置项'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class NightShiftDuty(models.Model):
    """夜班值班排班表"""
    DUTY_STATUS_CHOICES = [
        ('pending', '待检查'),
        ('completed', '已完成'),
    ]

    duty_date = models.DateField('值班日期')
    inspector = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='nightshift_duties', verbose_name='检查人',
    )
    status = models.CharField('状态', max_length=20, choices=DUTY_STATUS_CHOICES, default='pending')
    record = models.OneToOneField(
        'NightShiftRecord', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='duty_ref', verbose_name='检查记录',
    )
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='created_duties', verbose_name='排班人',
    )
    sms_sent_at = models.DateTimeField('短信通知时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '夜班值班排班'
        verbose_name_plural = '夜班值班排班'
        ordering = ['-duty_date']
        unique_together = ['duty_date']

    def __str__(self):
        name = self.inspector.get_full_name() or self.inspector.username
        return f"{self.duty_date} - {name} ({self.get_status_display()})"


class NightShiftRecord(models.Model):
    """夜班监护检查记录"""
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('submitted', '已提交'),
    ]

    duty = models.ForeignKey(
        NightShiftDuty, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='records', verbose_name='关联排班',
    )
    inspector = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='nightshift_records', verbose_name='巡检人',
    )
    inspection_date = models.DateField('巡检日期')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='draft')
    has_issues = models.BooleanField('存在问题', default=False)
    overall_remark = models.TextField('整体备注', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    submitted_at = models.DateTimeField('提交时间', null=True, blank=True)

    class Meta:
        verbose_name = '夜班检查记录'
        verbose_name_plural = '夜班检查记录'
        ordering = ['-inspection_date', '-created_at']

    def __str__(self):
        return f"{self.inspector} - {self.inspection_date}"


class NightShiftCheckResult(models.Model):
    """夜班监护检查结果（每项的检查结果）"""
    record = models.ForeignKey(
        NightShiftRecord, on_delete=models.CASCADE,
        related_name='results', verbose_name='检查记录',
    )
    category = models.ForeignKey(
        NightShiftCategory, on_delete=models.PROTECT, verbose_name='分类',
    )
    item = models.ForeignKey(
        NightShiftCheckItem, on_delete=models.PROTECT,
        null=True, blank=True, verbose_name='预置检查项',
        help_text='自填项时为空',
    )
    custom_name = models.CharField('自填项名称', max_length=200, blank=True,
                                   help_text='重点检查部位允许巡检人员自填')
    is_normal = models.BooleanField('是否正常', default=True)
    remark = models.TextField('异常备注', blank=True)

    class Meta:
        verbose_name = '夜班检查结果'
        verbose_name_plural = '夜班检查结果'

    def __str__(self):
        name = self.item.name if self.item else self.custom_name
        return f"{name}: {'正常' if self.is_normal else '异常'}"


class NightShiftIssue(models.Model):
    """夜班监护发现的问题（问题描述+整改情况）"""
    record = models.ForeignKey(
        NightShiftRecord, on_delete=models.CASCADE,
        related_name='issues', verbose_name='检查记录',
    )
    description = models.TextField('问题描述')
    rectification = models.TextField('整改情况', blank=True)
    is_resolved = models.BooleanField('已整改', default=False)

    class Meta:
        verbose_name = '夜班发现问题'
        verbose_name_plural = '夜班发现问题'

    def __str__(self):
        status = '已整改' if self.is_resolved else '未整改'
        return f"[{status}] {self.description[:30]}"


# ── 统一整改工单 ────────────────────────────────────────────────────────────
#
# 所有安全管理模块（隐患上报、除尘房巡检、夜班监护等）发现的问题，
# 都通过 RectificationOrder 统一走 "分派 → 整改 → 验证 → 闭环" 流程。
# 来源模块通过 (source_type, source_id) 多态引用回原始记录。
#
# 状态流转仅允许通过 rectification_service 进行，禁止直接 update status。

class RectificationOrder(models.Model):
    """统一整改工单"""

    SOURCE_TYPE_CHOICES = [
        ('hazard_report', '安全隐患上报'),
        ('dustroom_inspection', '除尘房巡检'),
        ('nightshift_check', '夜班监护检查'),
    ]

    STATUS_CHOICES = [
        ('pending', '待分派'),
        ('fixing', '整改中'),
        ('verifying', '待验证'),
        ('closed', '已闭环'),
        ('cancelled', '已取消'),
    ]

    SEVERITY_CHOICES = [
        ('general', '一般'),
        ('major', '重要'),
        ('critical', '严重'),
    ]

    # 来源（多态引用）
    source_type = models.CharField(
        '来源类型', max_length=30, choices=SOURCE_TYPE_CHOICES
    )
    source_id = models.PositiveIntegerField('来源记录ID')
    source_snapshot = models.JSONField(
        '来源快照', default=dict, blank=True,
        help_text='来源关键信息快照，原记录变更不影响工单上下文',
    )

    # 问题信息
    title = models.CharField('问题标题', max_length=200)
    description = models.TextField('问题描述')
    location_text = models.CharField('问题位置', max_length=200, blank=True)
    severity = models.CharField(
        '严重等级', max_length=20, choices=SEVERITY_CHOICES, default='general',
    )

    # 流转字段
    status = models.CharField(
        '状态', max_length=20, choices=STATUS_CHOICES, default='pending',
    )

    submitter = models.ForeignKey(
        User, on_delete=models.PROTECT,
        related_name='submitted_rectifications', verbose_name='提交人',
    )
    assignee = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_rectifications', verbose_name='整改责任人',
    )
    assigner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dispatched_rectifications', verbose_name='分派人',
    )
    assigned_at = models.DateTimeField('分派时间', null=True, blank=True)
    deadline = models.DateTimeField('整改期限', null=True, blank=True)

    rectify_description = models.TextField('整改说明', blank=True)
    rectified_at = models.DateTimeField('整改完成时间', null=True, blank=True)

    verifier = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verified_rectifications', verbose_name='验证人',
    )
    verifier_assigner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dispatched_verifier_rectifications',
        verbose_name='验证人分派人',
    )
    verifier_assigned_at = models.DateTimeField('验证人分派时间', null=True, blank=True)
    verified_at = models.DateTimeField('验证时间', null=True, blank=True)
    verify_remark = models.TextField('验证意见', blank=True)
    reject_count = models.PositiveSmallIntegerField('被驳回次数', default=0)

    overdue = models.BooleanField('已逾期', default=False)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '整改工单'
        verbose_name_plural = '整改工单'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['source_type', 'source_id']),
            models.Index(fields=['assignee', 'status']),
            models.Index(fields=['status', 'deadline']),
        ]

    def __str__(self) -> str:
        return f'[{self.get_source_type_display()}] {self.title}'


class RectificationImage(models.Model):
    """整改工单图片（问题现场 / 整改佐证）"""

    PHASE_CHOICES = [
        ('issue', '问题现场'),
        ('rectify', '整改佐证'),
    ]

    order = models.ForeignKey(
        RectificationOrder, on_delete=models.CASCADE,
        related_name='images', verbose_name='工单',
    )
    image = models.ImageField('图片', upload_to='rectifications/%Y/%m/')
    phase = models.CharField('阶段', max_length=10, choices=PHASE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '整改工单图片'
        verbose_name_plural = '整改工单图片'


class RectificationLog(models.Model):
    """整改工单操作日志（审计追溯）"""

    ACTION_CHOICES = [
        ('create', '创建'),
        ('assign', '分派'),
        ('reassign', '改派'),
        ('assign_verifier', '分派验证人'),
        ('submit_rectify', '提交整改'),
        ('verify_pass', '验证通过'),
        ('verify_reject', '验证驳回'),
        ('cancel', '取消'),
        ('auto_overdue', '逾期标记'),
    ]

    order = models.ForeignKey(
        RectificationOrder, on_delete=models.CASCADE,
        related_name='logs', verbose_name='工单',
    )
    action = models.CharField('操作', max_length=30, choices=ACTION_CHOICES)
    operator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='操作人',
    )
    from_status = models.CharField('前状态', max_length=20, blank=True)
    to_status = models.CharField('后状态', max_length=20, blank=True)
    remark = models.TextField('备注', blank=True)
    created_at = models.DateTimeField('时间', auto_now_add=True)

    class Meta:
        verbose_name = '整改操作日志'
        verbose_name_plural = '整改操作日志'
        ordering = ['-created_at']


class RectificationNotifyRecipient(models.Model):
    """整改中心新工单时接收短信通知的人员配置。

    可按来源类型过滤：source_type 为空时对所有来源生效，
    否则仅在匹配来源（hazard_report/dustroom_inspection/nightshift_check）时触发。
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='rectification_notify_subs', verbose_name='通知接收人',
    )
    source_type = models.CharField(
        '来源过滤', max_length=30, blank=True, default='',
        help_text='留空表示所有来源；否则仅匹配的来源会触发通知',
        choices=[('', '全部来源')] + RectificationOrder.SOURCE_TYPE_CHOICES,
    )
    enabled = models.BooleanField('启用', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '整改通知接收人'
        verbose_name_plural = '整改通知接收人'
        unique_together = ['user', 'source_type']
        ordering = ['user_id']

    def __str__(self):
        src = self.get_source_type_display() if self.source_type else '全部来源'
        return f'{self.user.username} ({src})'


class MezzanineRecord(models.Model):
    """夹层施工人员入离场记录"""

    name = models.CharField('姓名', max_length=50)
    phone = models.CharField('手机号', max_length=20)
    company = models.CharField('施工单位', max_length=100, blank=True)
    project = models.CharField('施工项目', max_length=200)
    count = models.PositiveIntegerField('人数', default=1)
    check_in_at = models.DateTimeField('入场时间', auto_now_add=True)
    check_out_at = models.DateTimeField('离场时间', null=True, blank=True)

    class Meta:
        verbose_name = '夹层施工记录'
        verbose_name_plural = '夹层施工记录'
        ordering = ['-check_in_at']

    def __str__(self):
        return f"{self.name} - {self.project} ({self.check_in_at:%Y-%m-%d})"
