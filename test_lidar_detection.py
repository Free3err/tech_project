#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест обнаружения человека через LiDAR
"""

import time
import sys
from lidar_interface import LiDARInterface
import config

def test_lidar_detection():
    """Тест обнаружения человека"""
    print("=" * 60)
    print("Тест обнаружения человека через LiDAR")
    print("=" * 60)
    print()
    
    # Инициализация LiDAR
    print(f"Подключение к LiDAR: {config.LIDAR_PORT}")
    try:
        lidar = LiDARInterface(config.LIDAR_PORT, config.LIDAR_BAUDRATE)
        print("✓ LiDAR подключен")
    except Exception as e:
        print(f"✗ Ошибка подключения LiDAR: {e}")
        return
    
    print()
    print("Параметры обнаружения:")
    print(f"  - Минимум точек: {config.PERSON_DETECTION_MIN_POINTS}")
    print(f"  - Расстояние кластеризации: {config.PERSON_DETECTION_CLUSTER_DISTANCE}м")
    print(f"  - Минимальный размер: {config.PERSON_MIN_CLUSTER_SIZE}м")
    print(f"  - Максимальный размер: {config.PERSON_MAX_CLUSTER_SIZE}м")
    print(f"  - Максимальная дальность: {config.LIDAR_MAX_RANGE}м")
    print()
    
    print("Начало сканирования (Ctrl+C для выхода)...")
    print()
    
    try:
        iteration = 0
        while True:
            iteration += 1
            
            # Получение сканирования
            scan = lidar.get_scan()
            
            # Фильтрация точек в допустимом диапазоне
            valid_points = [p for p in scan 
                          if config.LIDAR_MIN_RANGE <= p.distance <= config.LIDAR_MAX_RANGE]
            
            # Показать детали точек каждые 10 итераций
            if iteration % 10 == 0 and valid_points:
                print("\n\nДетали точек:")
                for i, p in enumerate(valid_points[:5]):  # Первые 5 точек
                    print(f"  Точка {i+1}: расстояние={p.distance:.3f}м, угол={p.angle:.2f}рад, интенсивность={p.intensity}")
                print()
            
            # Обнаружение человека
            person = lidar.detect_person()
            
            # Вывод информации
            print(f"\r[{iteration:04d}] Точек: {len(scan):4d} | Валидных: {len(valid_points):4d} | ", end="")
            
            if person:
                x, y = person
                distance = (x**2 + y**2)**0.5
                print(f"ЧЕЛОВЕК ОБНАРУЖЕН! Позиция: ({x:.2f}, {y:.2f})м, Расстояние: {distance:.2f}м", end="")
            else:
                print("Человек не обнаружен" + " " * 40, end="")
            
            sys.stdout.flush()
            time.sleep(0.2)  # 5 Гц
            
    except KeyboardInterrupt:
        print("\n\nОстановка...")
    finally:
        lidar.close()
        print("LiDAR закрыт")

if __name__ == '__main__':
    test_lidar_detection()
