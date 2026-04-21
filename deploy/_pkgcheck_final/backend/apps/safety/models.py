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
