from django.contrib.auth.models import User, Group
from rest_framework import serializers

from .models import UserProfile


def _get_role(user):
    groups = list(user.groups.values_list('name', flat=True))
    if '安全员' in groups:
        return 'safety_officer'
    elif '班组长' in groups:
        return 'team_leader'
    return 'worker'


ROLE_TO_GROUP = {
    'safety_officer': '安全员',
    'team_leader': '班组长',
    'worker': '员工',
}

VALID_ROLES = list(ROLE_TO_GROUP.keys())


class UserManageSerializer(serializers.ModelSerializer):
    """用于用户管理列表和详情展示"""
    name = serializers.CharField(source='first_name', read_only=True)
    role = serializers.SerializerMethodField()
    employee_id = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'name', 'role', 'employee_id', 'phone', 'is_active']

    def get_role(self, obj):
        return _get_role(obj)

    def get_employee_id(self, obj):
        try:
            return obj.profile.employee_id or ''
        except UserProfile.DoesNotExist:
            return ''

    def get_phone(self, obj):
        try:
            return obj.profile.phone
        except UserProfile.DoesNotExist:
            return ''


class UserCreateSerializer(serializers.Serializer):
    """创建用户"""
    username = serializers.CharField(max_length=150)
    name = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=6)
    role = serializers.ChoiceField(choices=VALID_ROLES)
    employee_id = serializers.CharField(max_length=50, allow_blank=True, required=False, default='')
    phone = serializers.CharField(max_length=20, allow_blank=True, required=False, default='')

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('用户名已存在')
        return value

    def validate_employee_id(self, value):
        if value and UserProfile.objects.filter(employee_id=value).exists():
            raise serializers.ValidationError('工号已存在')
        return value or None

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data['name'],
        )
        group_name = ROLE_TO_GROUP[validated_data['role']]
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.set([group])

        UserProfile.objects.create(
            user=user,
            employee_id=validated_data.get('employee_id') or None,
            phone=validated_data.get('phone', ''),
        )
        return user


class UserUpdateSerializer(serializers.Serializer):
    """编辑用户信息（不含 username 和 password）"""
    name = serializers.CharField(max_length=150)
    role = serializers.ChoiceField(choices=VALID_ROLES)
    employee_id = serializers.CharField(max_length=50, allow_blank=True, required=False, default='')
    phone = serializers.CharField(max_length=20, allow_blank=True, required=False, default='')

    def validate_employee_id(self, value):
        user = self.context.get('user')
        if value:
            qs = UserProfile.objects.filter(employee_id=value)
            if user:
                qs = qs.exclude(user=user)
            if qs.exists():
                raise serializers.ValidationError('工号已存在')
        return value or None

    def update(self, user, validated_data):
        user.first_name = validated_data['name']
        user.save(update_fields=['first_name'])

        group_name = ROLE_TO_GROUP[validated_data['role']]
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.set([group])

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.employee_id = validated_data.get('employee_id') or None
        profile.phone = validated_data.get('phone', '')
        profile.save(update_fields=['employee_id', 'phone', 'updated_at'])
        return user


class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=6)
