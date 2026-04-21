from rest_framework.permissions import BasePermission

from .models import DustRoomInspector


def _in_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


class IsSafetyOfficer(BasePermission):
    """只有安全员可以操作"""
    message = '只有安全员可以执行此操作'

    def has_permission(self, request, view):
        return request.user.is_authenticated and _in_group(request.user, '安全员')


class IsAssignee(BasePermission):
    """只有该隐患的整改责任人可以提交整改"""
    message = '只有整改责任人可以提交整改'

    def has_object_permission(self, request, view, obj):
        return request.user == obj.assignee


class IsDustRoomInspector(BasePermission):
    """用户必须是已分配的除尘房巡检人员"""
    message = '您未被分配除尘房巡检角色'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return DustRoomInspector.objects.filter(user=request.user).exists()
