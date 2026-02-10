#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from lidar_interface import LiDARInterface
import config

print("=" * 60)
print("Тест LDROBOT D500")
print("=" * 60)
print()

lidar = LiDARInterface()

print("Начало сканирования (Ctrl+C для выхода)...")
print()

try:
    iteration = 0
    while True:
        iteration += 1
        
        scan = lidar.get_scan()
        person = lidar.detect_person()
        
        print(f"\r[{iteration:04d}] Точек: {len(scan):4d} | ", end="")
        
        if person and len(scan) >= 3:
            x, y = person
            dist = (x**2 + y**2)**0.5
            print(f"ЧЕЛОВЕК! Расстояние: {dist:.2f}м" + " " * 20, end="")
        else:
            print("Нет обнаружения" + " " * 40, end="")
        
        time.sleep(0.2)

except KeyboardInterrupt:
    print("\n\nОстановка...")
finally:
    lidar.close()
