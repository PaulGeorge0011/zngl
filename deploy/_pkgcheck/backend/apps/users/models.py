from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    """Django User 的扩展信息（工号、联系电话）"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile', verbose_name='用户'
    )
    employee_id = models.CharField(
        '工号', max_length=50, unique=True, blank=True, null=True, default=None
    )
    phone = models.CharField('联系电话', max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '用户资料'
        verbose_name_plural = '用户资料'

    def __str__(self):
        return f"{self.user.username} 的资料"
