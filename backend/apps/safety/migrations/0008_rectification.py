"""统一整改工单 — 建表 + 存量 HazardReport 数据回填。

迁移策略:
- 正向: 创建 RectificationOrder / RectificationImage / RectificationLog 三张表,
        并把每一条 HazardReport 复制为一条 source_type='hazard_report' 的工单,
        同时把 HazardImage 复制到 RectificationImage。
- 反向: 仅删表。不回写 HazardReport, 因为原表数据一直保留并独立维护。

注意: 不触碰旧表 HazardReport / HazardImage, 保证已部署环境的原有数据与接口不受影响。
"""
from django.db import migrations, models
import django.db.models.deletion


def _severity_from_level(level: str) -> str:
    """hazard.level (general/major) -> rectification.severity."""
    if level == 'major':
        return 'critical'
    return 'general'


def _hazard_status_to_rect_status(status: str) -> str:
    """hazard.status -> rectification.status。

    五态 (pending/fixing/verifying/closed/rejected) 合并为四态
    (pending/fixing/verifying/closed) — rejected 归入 fixing（重做中）。
    """
    mapping = {
        'pending': 'pending',
        'fixing': 'fixing',
        'verifying': 'verifying',
        'closed': 'closed',
        'rejected': 'fixing',
    }
    return mapping.get(status, 'pending')


def backfill_from_hazard(apps, schema_editor):
    """把存量 HazardReport 复制成 RectificationOrder。"""
    HazardReport = apps.get_model('safety', 'HazardReport')
    HazardImage = apps.get_model('safety', 'HazardImage')
    Order = apps.get_model('safety', 'RectificationOrder')
    OrderImage = apps.get_model('safety', 'RectificationImage')
    OrderLog = apps.get_model('safety', 'RectificationLog')

    for hazard in HazardReport.objects.all().iterator():
        location_text = hazard.location.name if hazard.location_id else ''
        if hazard.location_detail:
            location_text = f'{location_text} {hazard.location_detail}'.strip()

        order = Order.objects.create(
            source_type='hazard_report',
            source_id=hazard.id,
            source_snapshot={
                'hazard_id': hazard.id,
                'level': hazard.level,
                'location_id': hazard.location_id,
                'location_detail': hazard.location_detail,
            },
            title=hazard.title,
            description=hazard.description,
            location_text=location_text,
            severity=_severity_from_level(hazard.level),
            status=_hazard_status_to_rect_status(hazard.status),
            submitter_id=hazard.reporter_id,
            assignee_id=hazard.assignee_id,
            assigner_id=hazard.assigned_by_id,
            assigned_at=hazard.assigned_at,
            deadline=None,
            rectify_description=hazard.fix_description or '',
            rectified_at=hazard.fixed_at,
            verifier_id=hazard.verified_by_id,
            verified_at=hazard.verified_at,
            verify_remark=hazard.verify_remark or '',
            reject_count=1 if hazard.status == 'rejected' else 0,
            created_at=hazard.created_at,
            updated_at=hazard.updated_at,
        )

        # 复制图片
        for img in HazardImage.objects.filter(hazard=hazard):
            phase = 'rectify' if img.phase == 'fix' else 'issue'
            OrderImage.objects.create(
                order=order,
                image=img.image,
                phase=phase,
                created_at=img.created_at,
            )

        # 记录一条 create 日志
        OrderLog.objects.create(
            order=order,
            action='create',
            operator_id=hazard.reporter_id,
            from_status='',
            to_status=order.status,
            remark='由存量隐患上报迁移',
            created_at=hazard.created_at,
        )


def unbackfill(apps, schema_editor):
    """反向迁移: 清空所有 source_type='hazard_report' 的工单。"""
    Order = apps.get_model('safety', 'RectificationOrder')
    Order.objects.filter(source_type='hazard_report').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('safety', '0007_nightshiftduty_sms_sent_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='RectificationOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_type', models.CharField(choices=[
                    ('hazard_report', '安全隐患上报'),
                    ('dustroom_inspection', '除尘房巡检'),
                    ('nightshift_check', '夜班监护检查'),
                ], max_length=30, verbose_name='来源类型')),
                ('source_id', models.PositiveIntegerField(verbose_name='来源记录ID')),
                ('source_snapshot', models.JSONField(blank=True, default=dict, help_text='来源关键信息快照，原记录变更不影响工单上下文', verbose_name='来源快照')),
                ('title', models.CharField(max_length=200, verbose_name='问题标题')),
                ('description', models.TextField(verbose_name='问题描述')),
                ('location_text', models.CharField(blank=True, max_length=200, verbose_name='问题位置')),
                ('severity', models.CharField(choices=[
                    ('general', '一般'), ('major', '重要'), ('critical', '严重'),
                ], default='general', max_length=20, verbose_name='严重等级')),
                ('status', models.CharField(choices=[
                    ('pending', '待分派'), ('fixing', '整改中'),
                    ('verifying', '待验证'), ('closed', '已闭环'),
                    ('cancelled', '已取消'),
                ], default='pending', max_length=20, verbose_name='状态')),
                ('assigned_at', models.DateTimeField(blank=True, null=True, verbose_name='分派时间')),
                ('deadline', models.DateTimeField(blank=True, null=True, verbose_name='整改期限')),
                ('rectify_description', models.TextField(blank=True, verbose_name='整改说明')),
                ('rectified_at', models.DateTimeField(blank=True, null=True, verbose_name='整改完成时间')),
                ('verified_at', models.DateTimeField(blank=True, null=True, verbose_name='验证时间')),
                ('verify_remark', models.TextField(blank=True, verbose_name='验证意见')),
                ('reject_count', models.PositiveSmallIntegerField(default=0, verbose_name='被驳回次数')),
                ('overdue', models.BooleanField(default=False, verbose_name='已逾期')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('assignee', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='assigned_rectifications',
                    to='auth.user', verbose_name='整改责任人')),
                ('assigner', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='dispatched_rectifications',
                    to='auth.user', verbose_name='分派人')),
                ('submitter', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='submitted_rectifications',
                    to='auth.user', verbose_name='提交人')),
                ('verifier', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='verified_rectifications',
                    to='auth.user', verbose_name='验证人')),
            ],
            options={
                'verbose_name': '整改工单',
                'verbose_name_plural': '整改工单',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='rectificationorder',
            index=models.Index(fields=['source_type', 'source_id'], name='safety_rect_source__a7f898_idx'),
        ),
        migrations.AddIndex(
            model_name='rectificationorder',
            index=models.Index(fields=['assignee', 'status'], name='safety_rect_assigne_a74ffa_idx'),
        ),
        migrations.AddIndex(
            model_name='rectificationorder',
            index=models.Index(fields=['status', 'deadline'], name='safety_rect_status_15fbd8_idx'),
        ),
        migrations.CreateModel(
            name='RectificationImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='rectifications/%Y/%m/', verbose_name='图片')),
                ('phase', models.CharField(choices=[
                    ('issue', '问题现场'), ('rectify', '整改佐证'),
                ], max_length=10, verbose_name='阶段')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='images',
                    to='safety.rectificationorder', verbose_name='工单')),
            ],
            options={
                'verbose_name': '整改工单图片',
                'verbose_name_plural': '整改工单图片',
            },
        ),
        migrations.CreateModel(
            name='RectificationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[
                    ('create', '创建'), ('assign', '分派'), ('reassign', '改派'),
                    ('submit_rectify', '提交整改'),
                    ('verify_pass', '验证通过'), ('verify_reject', '验证驳回'),
                    ('cancel', '取消'), ('auto_overdue', '逾期标记'),
                ], max_length=30, verbose_name='操作')),
                ('from_status', models.CharField(blank=True, max_length=20, verbose_name='前状态')),
                ('to_status', models.CharField(blank=True, max_length=20, verbose_name='后状态')),
                ('remark', models.TextField(blank=True, verbose_name='备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='时间')),
                ('order', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='logs',
                    to='safety.rectificationorder', verbose_name='工单')),
                ('operator', models.ForeignKey(blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='auth.user', verbose_name='操作人')),
            ],
            options={
                'verbose_name': '整改操作日志',
                'verbose_name_plural': '整改操作日志',
                'ordering': ['-created_at'],
            },
        ),
        migrations.RunPython(backfill_from_hazard, unbackfill),
    ]
