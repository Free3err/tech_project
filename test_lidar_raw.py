#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест сырых данных LiDAR
Показывает что именно получает LiDAR
"""

import serial
import time
import struct

PORT = '/dev/ttyUSB0'
BAUDRATE = 230400
HEADER = 0x54

def test_raw_lidar():
    """Тест сырых данных LiDAR"""
    print("=" * 60)
    print("Тест сырых данных LiDAR")
    print("=" * 60)
    print(f"Порт: {PORT}")
    print(f"Скорость: {BAUDRATE}")
    print()
    
    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=1.0)
        print("✓ Порт открыт")
        print()
        print("Чтение данных (Ctrl+C для выхода)...")
        print()
        
        packet_count = 0
        byte_count = 0
        
        while True:
            # Читаем байт
            byte = ser.read(1)
            if not byte:
                continue
            
            byte_count += 1
            byte_val = byte[0]
            
            # Ищем заголовок пакета
            if byte_val == HEADER:
                packet_count += 1
                
                # Читаем остаток пакета (46 байт)
                packet_data = ser.read(46)
                
                if len(packet_data) == 46:
                    print(f"\r[Пакет {packet_count:04d}] Байтов: {byte_count:06d} | ", end="")
                    
                    # Парсим первые несколько точек для проверки
                    try:
                        # Байты 2-3: начальный угол
                        start_angle = struct.unpack('<H', packet_data[0:2])[0] / 100.0
                        
                        # Байты 4-5: конечный угол  
                        end_angle = struct.unpack('<H', packet_data[2:4])[0] / 100.0
                        
                        # Количество точек в пакете
                        points_in_packet = 12
                        
                        print(f"Углы: {start_angle:.1f}° - {end_angle:.1f}° | Точек: {points_in_packet}", end="")
                        
                        # Парсим первую точку
                        point_offset = 4  # Данные точек начинаются с байта 4
                        distance = struct.unpack('<H', packet_data[point_offset:point_offset+2])[0]
                        intensity = packet_data[point_offset+2]
                        
                        print(f" | Точка 1: {distance}мм, яркость: {intensity}", end="")
                        
                    except Exception as e:
                        print(f"Ошибка парсинга: {e}", end="")
                else:
                    print(f"\r[Пакет {packet_count:04d}] НЕПОЛНЫЙ ПАКЕТ: {len(packet_data)} байт", end="")
                
                print()
                
            # Показываем прогресс каждые 1000 байт
            if byte_count % 1000 == 0:
                print(f"\rПрочитано байтов: {byte_count:06d}, пакетов: {packet_count:04d}", end="")
                
    except KeyboardInterrupt:
        print("\n\nОстановка...")
    except Exception as e:
        print(f"\n\nОшибка: {e}")
    finally:
        if 'ser' in locals():
            ser.close()
            print("Порт закрыт")

if __name__ == '__main__':
    test_raw_lidar()
