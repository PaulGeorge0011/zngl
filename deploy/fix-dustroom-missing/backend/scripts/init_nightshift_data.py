"""
初始化夜班监护检查种子数据：3个检查分类 + 预置检查项
运行方式：python manage.py shell < scripts/init_nightshift_data.py
"""
from apps.safety.models import NightShiftCategory, NightShiftCheckItem

CATEGORIES = [
    {
        'name': '作业行为',
        'allows_custom': False,
        'sort_order': 1,
        'items': [
            '佩戴劳动防护用品',
            '操作规程执行情况',
            '交接班手续完整性',
            '禁止违章作业',
            '岗位人员在岗情况',
            '作业现场秩序',
        ],
    },
    {
        'name': '工器具',
        'allows_custom': False,
        'sort_order': 2,
        'items': [
            '工器具完好性',
            '工器具摆放规范',
            '特种工器具检验合格',
            '工器具清洁保养',
        ],
    },
    {
        'name': '重点检查部位',
        'allows_custom': True,
        'sort_order': 3,
        'items': [
            '配电室',
            '除尘房',
            '加料间',
            '烘丝机区域',
            '储丝房',
            '空调机组',
        ],
    },
]

for cat_data in CATEGORIES:
    cat, created = NightShiftCategory.objects.get_or_create(
        name=cat_data['name'],
        defaults={
            'allows_custom': cat_data['allows_custom'],
            'sort_order': cat_data['sort_order'],
        },
    )
    status = '新建' if created else '已存在'
    print(f"  分类 {cat_data['name']}（允许自填={cat_data['allows_custom']}）: {status}")

    for idx, item_name in enumerate(cat_data['items']):
        _, item_created = NightShiftCheckItem.objects.get_or_create(
            category=cat, name=item_name,
            defaults={'sort_order': idx * 10},
        )
        if item_created:
            print(f"    检查项: {item_name}")

print("\n夜班监护检查数据初始化完成！")
