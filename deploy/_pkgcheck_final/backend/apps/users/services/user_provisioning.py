from django.contrib.auth.models import Group, User
from django.db import transaction

from apps.users.models import UserProfile
from apps.users.services.sso import SsoUserInfo

DEFAULT_GROUP_NAME = '员工'
USERNAME_PREFIX = 'ynzy_'


def build_unique_username(employee_id: str) -> str:
    candidates = [employee_id, f'{USERNAME_PREFIX}{employee_id}']
    for candidate in candidates:
        if not User.objects.filter(username=candidate).exists():
            return candidate

    index = 1
    while True:
        candidate = f'{USERNAME_PREFIX}{employee_id}_{index}'
        if not User.objects.filter(username=candidate).exists():
            return candidate
        index += 1


@transaction.atomic
def provision_user_from_sso(info: SsoUserInfo) -> User:
    profile = UserProfile.objects.select_related('user').filter(employee_id=info.employee_id).first()
    if profile:
        return profile.user

    username = build_unique_username(info.employee_id)
    user = User(username=username, first_name=info.display_name, is_active=True)
    user.set_unusable_password()
    user.save()

    group, _ = Group.objects.get_or_create(name=DEFAULT_GROUP_NAME)
    user.groups.set([group])
    UserProfile.objects.create(user=user, employee_id=info.employee_id, phone=info.phone)
    return user
