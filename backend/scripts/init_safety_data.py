"""
初始化安全模块种子数据：区域 + 演示用户
运行方式：python manage.py shell < scripts/init_safety_data.py
"""
from django.contrib.auth.models import User, Group
from apps.safety.models import Location

# ── 区域 ──────────────────────────────────────────────────────────────────────
LOCATIONS = [
    ('松散回潮', 1), ('切片', 2), ('加料', 3), ('烘丝', 4),
    ('加香', 5), ('储丝', 6), ('配送', 7), ('公共区域', 8), ('办公区域', 9),
]

created = 0
for name, order in LOCATIONS:
    _, made = Location.objects.get_or_create(name=name, defaults={'sort_order': order})
    if made:
        created += 1

print(f"区域：新建 {created} 条，已有 {len(LOCATIONS) - created} 条")

# ── 角色组 ────────────────────────────────────────────────────────────────────
GROUP_NAMES = ['员工', '班组长', '安全员']
groups = {}
for gname in GROUP_NAMES:
    g, _ = Group.objects.get_or_create(name=gname)
    groups[gname] = g

print(f"角色组已就绪：{GROUP_NAMES}")

# ── 演示用户 ──────────────────────────────────────────────────────────────────
DEMO_USERS = [
    ('admin',   '系统管理员', 'admin123',   '安全员'),
    ('leader1', '班组长一',   'leader123',  '班组长'),
    ('worker1', '员工一',     'worker123',  '员工'),
]

for username, fullname, password, role in DEMO_USERS:
    if not User.objects.filter(username=username).exists():
        u = User.objects.create_user(
            username=username,
            password=password,
            first_name=fullname,
            is_staff=(role == '安全员'),
        )
        u.groups.add(groups[role])
        print(f"  创建用户 {username}（{role}）")
    else:
        print(f"  用户 {username} 已存在，跳过")

print("种子数据初始化完成")
