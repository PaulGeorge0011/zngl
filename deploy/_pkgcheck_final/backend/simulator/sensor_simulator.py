"""
传感器数据模拟器

运行方式：
    cd backend
    python -m simulator.run_simulator

功能：
    - 从后端 API 拉取所有设备和监控点
    - 每 5 秒为每个监控点生成一条拟真数据
    - 使用高斯噪声随机游走，模拟真实传感器特征
    - 周期性触发渐进式异常，模拟故障前兆
"""
import time
import random
import logging
from datetime import datetime
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# 各参数类型的基准配置
PARAM_CONFIGS = {
    'temperature': {'base': 65.0, 'noise_std': 0.5, 'walk_factor': 0.3},
    'current': {'base': 12.0, 'noise_std': 0.3, 'walk_factor': 0.2},
    'vibration': {'base': 2.5, 'noise_std': 0.1, 'walk_factor': 0.05},
}


class SensorSimulator:
    def __init__(self, api_base: str = "http://localhost:8000"):
        self.api_base = api_base
        self.monitor_points: list[dict] = []
        self.current_values: dict[int, float] = {}  # point_id -> current value
        self.anomaly_steps: dict[int, int] = {}  # point_id -> anomaly progress (0=normal)
        self.tick_count = 0

    def load_monitor_points(self):
        """从 API 拉取所有设备及其监控点"""
        try:
            resp = requests.get(f"{self.api_base}/api/equipment/equipments/?page_size=100")
            resp.raise_for_status()
            equipments = resp.json().get('results', [])

            self.monitor_points = []
            for eq in equipments:
                detail = requests.get(f"{self.api_base}/api/equipment/equipments/{eq['id']}/")
                detail.raise_for_status()
                eq_data = detail.json()
                for point in eq_data.get('monitor_points', []):
                    point['equipment_name'] = eq_data['name']
                    self.monitor_points.append(point)
                    # 初始化当前值
                    config = PARAM_CONFIGS.get(point['param_type'], PARAM_CONFIGS['temperature'])
                    self.current_values[point['id']] = config['base']
                    self.anomaly_steps[point['id']] = 0

            logger.info(f"加载 {len(self.monitor_points)} 个监控点")
        except Exception as e:
            logger.error(f"加载监控点失败: {e}")
            raise

    def generate_value(self, point: dict) -> float:
        """生成拟真传感器值（随机游走 + 可选异常）"""
        point_id = point['id']
        config = PARAM_CONFIGS.get(point['param_type'], PARAM_CONFIGS['temperature'])

        current = self.current_values[point_id]
        step = self.anomaly_steps.get(point_id, 0)

        # 随机游走：向基准值回归 + 高斯噪声
        drift = (config['base'] - current) * 0.05  # 回归力
        noise = random.gauss(0, config['noise_std'])
        current = current + drift + noise * config['walk_factor']

        # 异常叠加：逐步偏离
        if step > 0:
            threshold = point.get('threshold', {})
            warning_high = threshold.get('warning_high') if threshold else None
            if warning_high:
                target = warning_high * 1.1  # 超过报警线
            else:
                target = config['base'] * 1.3
            anomaly_offset = (target - config['base']) * (step / 10.0)
            current += anomaly_offset * 0.3

            # 异常递进
            if step < 15:
                self.anomaly_steps[point_id] = step + 1
            else:
                # 异常结束，回归正常
                self.anomaly_steps[point_id] = 0

        self.current_values[point_id] = current
        return round(current, 2)

    def maybe_trigger_anomaly(self):
        """每 60 个 tick（约 5 分钟）随机选一个点触发异常"""
        if self.tick_count % 60 == 0 and self.tick_count > 0:
            candidates = [p for p in self.monitor_points if self.anomaly_steps.get(p['id'], 0) == 0]
            if candidates:
                target = random.choice(candidates)
                self.anomaly_steps[target['id']] = 1
                logger.info(f"触发异常: {target['equipment_name']} - {target['name']}")

    def send_readings(self, readings: list[dict]):
        """批量发送数据到后端"""
        try:
            resp = requests.post(
                f"{self.api_base}/api/monitoring/readings/",
                json={'readings': readings},
                timeout=5,
            )
            if resp.status_code == 201:
                result = resp.json()
                alarms = result.get('alarms_triggered', [])
                if alarms:
                    logger.warning(f"触发报警: {alarms}")
            else:
                logger.warning(f"发送数据响应: {resp.status_code}")
        except Exception as e:
            logger.error(f"发送数据失败: {e}")

    def run(self, interval: int = 5):
        """主循环"""
        self.load_monitor_points()

        if not self.monitor_points:
            logger.error("没有监控点，请先通过 API 或 Admin 创建设备和监控点")
            return

        logger.info(f"模拟器启动，间隔 {interval} 秒，{len(self.monitor_points)} 个监控点")

        while True:
            self.maybe_trigger_anomaly()

            readings = []
            now = datetime.now().isoformat()

            for point in self.monitor_points:
                value = self.generate_value(point)
                readings.append({
                    'monitor_point': point['id'],
                    'value': value,
                    'recorded_at': now,
                })

            self.send_readings(readings)
            self.tick_count += 1

            # 打印状态
            if self.tick_count % 12 == 0:  # 每分钟打印一次
                logger.info(f"Tick {self.tick_count}: 发送 {len(readings)} 条数据")

            time.sleep(interval)
