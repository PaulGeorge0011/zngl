"""标记已逾期的整改工单。

用法:
    python manage.py mark_overdue_rectifications

建议通过 crontab 每小时执行一次:
    0 * * * * cd /path/to/zngl/backend && /path/to/venv/bin/python \
        manage.py mark_overdue_rectifications >> /var/log/zngl/overdue.log 2>&1
"""
from django.core.management.base import BaseCommand

from apps.safety import rectification_service as svc


class Command(BaseCommand):
    help = '扫描并标记已逾期的整改工单（状态为 pending/fixing 且超过 deadline）'

    def handle(self, *args, **options):
        count = svc.mark_overdue()
        self.stdout.write(self.style.SUCCESS(f'已标记 {count} 条逾期工单'))
