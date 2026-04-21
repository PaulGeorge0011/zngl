"""
初始化演示数据：创建设备、监控点、阈值规则

使用方式：
    cd backend
    python manage.py shell < scripts/init_demo_data.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.equipment.models import Equipment, MonitorPoint
from apps.monitoring.models import ThresholdRule

# 清理旧数据
print("清理旧数据...")
Equipment.objects.all().delete()

# 设备 1：切丝机
eq1 = Equipment.objects.create(
    name='切丝机-01',
    code='QSJ-001',
    location='制丝车间A区',
    description='HXD型切丝机，用于将烟叶切成规定宽度的烟丝',
    status='running',
)
print(f"创建设备: {eq1}")

points_1 = [
    {'name': '主轴温度', 'param_key': 'temperature_main', 'unit': '℃', 'param_type': 'temperature',
     'thresholds': {'warning_high': 75, 'warning_low': 10, 'alarm_high': 85, 'alarm_low': 5}},
    {'name': '主电机电流', 'param_key': 'current_main', 'unit': 'A', 'param_type': 'current',
     'thresholds': {'warning_high': 18, 'warning_low': 3, 'alarm_high': 22, 'alarm_low': 1}},
    {'name': '刀辊振动', 'param_key': 'vibration_roller', 'unit': 'mm/s', 'param_type': 'vibration',
     'thresholds': {'warning_high': 4.5, 'warning_low': None, 'alarm_high': 7.0, 'alarm_low': None}},
]

for p_data in points_1:
    thresholds = p_data.pop('thresholds')
    point = MonitorPoint.objects.create(equipment=eq1, **p_data)
    ThresholdRule.objects.create(monitor_point=point, **thresholds)
    print(f"  监控点: {point.name} ({point.unit})")

# 设备 2：烘丝机
eq2 = Equipment.objects.create(
    name='烘丝机-01',
    code='HSJ-001',
    location='制丝车间B区',
    description='SH型滚筒式烘丝机，用于烘干和膨胀烟丝',
    status='running',
)
print(f"创建设备: {eq2}")

points_2 = [
    {'name': '滚筒温度', 'param_key': 'temperature_drum', 'unit': '℃', 'param_type': 'temperature',
     'thresholds': {'warning_high': 120, 'warning_low': 60, 'alarm_high': 140, 'alarm_low': 40}},
    {'name': '热风电机电流', 'param_key': 'current_fan', 'unit': 'A', 'param_type': 'current',
     'thresholds': {'warning_high': 25, 'warning_low': 5, 'alarm_high': 30, 'alarm_low': 2}},
    {'name': '滚筒振动', 'param_key': 'vibration_drum', 'unit': 'mm/s', 'param_type': 'vibration',
     'thresholds': {'warning_high': 5.0, 'warning_low': None, 'alarm_high': 8.0, 'alarm_low': None}},
]

for p_data in points_2:
    thresholds = p_data.pop('thresholds')
    point = MonitorPoint.objects.create(equipment=eq2, **p_data)
    ThresholdRule.objects.create(monitor_point=point, **thresholds)
    print(f"  监控点: {point.name} ({point.unit})")

# 设备 3：加料机
eq3 = Equipment.objects.create(
    name='加料机-01',
    code='JLJ-001',
    location='制丝车间A区',
    description='滚筒式加料机，用于向烟丝中添加料液',
    status='stopped',
)
print(f"创建设备: {eq3}")

points_3 = [
    {'name': '料液温度', 'param_key': 'temperature_liquid', 'unit': '℃', 'param_type': 'temperature',
     'thresholds': {'warning_high': 50, 'warning_low': 20, 'alarm_high': 60, 'alarm_low': 15}},
    {'name': '搅拌电机电流', 'param_key': 'current_mixer', 'unit': 'A', 'param_type': 'current',
     'thresholds': {'warning_high': 15, 'warning_low': 2, 'alarm_high': 20, 'alarm_low': 1}},
]

for p_data in points_3:
    thresholds = p_data.pop('thresholds')
    point = MonitorPoint.objects.create(equipment=eq3, **p_data)
    ThresholdRule.objects.create(monitor_point=point, **thresholds)
    print(f"  监控点: {point.name} ({point.unit})")

print(f"\n初始化完成: {Equipment.objects.count()} 台设备, {MonitorPoint.objects.count()} 个监控点")
