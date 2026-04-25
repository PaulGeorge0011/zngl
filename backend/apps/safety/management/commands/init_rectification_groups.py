"""
初始化整改中心所需的用户组
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = '初始化整改中心所需的用户组'

    def handle(self, *args, **options):
        # 创建"整改分派人"组
        group, created = Group.objects.get_or_create(name='整改分派人')

        if created:
            self.stdout.write(
                self.style.SUCCESS('成功创建用户组: 整改分派人')
            )
        else:
            self.stdout.write(
                self.style.WARNING('用户组已存在: 整改分派人')
            )

        # 确保"安全员"组存在
        safety_group, safety_created = Group.objects.get_or_create(name='安全员')

        if safety_created:
            self.stdout.write(
                self.style.SUCCESS('成功创建用户组: 安全员')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('用户组已存在: 安全员')
            )

        self.stdout.write(
            self.style.SUCCESS('\n整改中心用户组初始化完成！')
        )
