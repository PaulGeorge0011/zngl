#!/usr/bin/env python
"""
传感器模拟器入口

使用方式：
    cd backend
    python -m simulator.run_simulator
    python -m simulator.run_simulator --interval 3 --api http://localhost:8000
"""
import argparse
import logging

from .sensor_simulator import SensorSimulator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)


def main():
    parser = argparse.ArgumentParser(description='传感器数据模拟器')
    parser.add_argument('--interval', type=int, default=5, help='数据发送间隔（秒）')
    parser.add_argument('--api', type=str, default='http://localhost:8000', help='后端 API 地址')
    args = parser.parse_args()

    simulator = SensorSimulator(api_base=args.api)
    try:
        simulator.run(interval=args.interval)
    except KeyboardInterrupt:
        print("\n模拟器已停止")


if __name__ == '__main__':
    main()
