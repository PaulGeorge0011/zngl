"""
初始化除尘房巡检种子数据：除尘房 + 四角色巡检模板 + 检查项 + 演示人员分配
运行方式：python manage.py shell < scripts/init_dustroom_data.py
"""
from django.contrib.auth.models import User
from apps.safety.models import (
    DustRoom, InspectionTemplate, InspectionItem, DustRoomInspector,
)

# ── 除尘房 ────────────────────────────────────────────────────────────────────

ROOMS = [
    ('1号除尘房', 'DCF-01', '松散回潮工段除尘房', 1),
    ('2号除尘房', 'DCF-02', '切片加料工段除尘房', 2),
    ('3号除尘房', 'DCF-03', '烘丝加香工段除尘房', 3),
]

for name, code, desc, order in ROOMS:
    obj, created = DustRoom.objects.get_or_create(
        code=code, defaults={'name': name, 'description': desc, 'sort_order': order}
    )
    print(f"  除尘房 {name}: {'新建' if created else '已存在'}")

# ── 巡检模板 + 检查项 ────────────────────────────────────────────────────────

TEMPLATES = {
    'electrical': {
        'name': '电气修理工日常巡检',
        'frequency': 'daily',
        'items': [
            ('除尘风机电机运行电流', 'number', 'A'),
            ('除尘风机电机运行温度', 'number', '℃'),
            ('除尘风机电机绝缘是否正常', 'checkbox', ''),
            ('配电柜指示灯是否正常', 'checkbox', ''),
            ('配电柜内有无异味/异响', 'checkbox', ''),
            ('电气线路有无破损/老化', 'checkbox', ''),
            ('接地线是否完好', 'checkbox', ''),
            ('温度传感器是否正常', 'checkbox', ''),
        ],
    },
    'mechanical': {
        'name': '机械修理工日常巡检',
        'frequency': 'daily',
        'items': [
            ('除尘风机振动是否正常', 'checkbox', ''),
            ('除尘风机轴承温度', 'number', '℃'),
            ('风机皮带松紧度是否正常', 'checkbox', ''),
            ('除尘管道有无泄漏', 'checkbox', ''),
            ('除尘管道连接处是否紧固', 'checkbox', ''),
            ('脉冲阀工作是否正常', 'checkbox', ''),
            ('灰斗卸灰装置是否正常', 'checkbox', ''),
            ('压差表读数', 'number', 'Pa'),
        ],
    },
    'operator': {
        'name': '操作工日常巡检',
        'frequency': 'per_shift',
        'items': [
            ('除尘系统运行状态是否正常', 'checkbox', ''),
            ('除尘房内有无粉尘堆积', 'checkbox', ''),
            ('除尘房门窗是否关闭', 'checkbox', ''),
            ('消防器材是否完好在位', 'checkbox', ''),
            ('安全标识是否完好', 'checkbox', ''),
            ('除尘房内温度', 'number', '℃'),
            ('运行异常情况说明', 'text', ''),
        ],
    },
    'safety': {
        'name': '安全员日常巡检',
        'frequency': 'daily',
        'items': [
            ('除尘房防爆措施是否到位', 'checkbox', ''),
            ('泄爆口是否完好无堵塞', 'checkbox', ''),
            ('静电接地是否有效', 'checkbox', ''),
            ('禁烟禁火标识是否醒目', 'checkbox', ''),
            ('消防设施是否完好有效', 'checkbox', ''),
            ('应急疏散通道是否畅通', 'checkbox', ''),
            ('粉尘浓度监测装置是否正常', 'checkbox', ''),
            ('操作规程是否张贴到位', 'checkbox', ''),
            ('现场6S管理状况', 'select', ''),
            ('安全隐患及整改建议', 'text', ''),
        ],
    },
}

SIX_S_OPTIONS = ['优', '良', '中', '差']

for role, tpl_data in TEMPLATES.items():
    tpl, created = InspectionTemplate.objects.get_or_create(
        role=role,
        defaults={'name': tpl_data['name'], 'frequency': tpl_data['frequency']},
    )
    print(f"  模板 {tpl_data['name']}: {'新建' if created else '已存在'}")

    for idx, (item_name, item_type, unit) in enumerate(tpl_data['items']):
        options = SIX_S_OPTIONS if item_name == '现场6S管理状况' else []
        _, item_created = InspectionItem.objects.get_or_create(
            template=tpl, name=item_name,
            defaults={
                'item_type': item_type,
                'unit': unit,
                'options': options,
                'sort_order': idx * 10,
            },
        )
        if item_created:
            print(f"    检查项: {item_name}")

# ── 演示人员分配 ──────────────────────────────────────────────────────────────

admin_user = User.objects.filter(username='admin').first()
if admin_user:
    _, created = DustRoomInspector.objects.get_or_create(user=admin_user, role='safety')
    if created:
        print(f"  分配 admin 为安全员巡检人员")
    _, created = DustRoomInspector.objects.get_or_create(user=admin_user, role='electrical')
    if created:
        print(f"  分配 admin 为电气修理工巡检人员（演示用）")

print("\n除尘房巡检数据初始化完成！")
