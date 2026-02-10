#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Упрощенный детектор человека для LDROBOT D500
Работает по принципу изменения расстояний
"""

import serial
import time
import struct
import logging
from typing import Optional, Tuple, List
import config

logger = logging.getLogger(__name__)


class SimplePersonDetector:
    """
    Упрощенный детектор человека через LiDAR
    
    Принцип работы:
    1. Читаем все расстояния от LiDAR
    2. Ищем точки в диапазоне 0.3-2.0 метра
    3. Если есть группа близких точек - это человек
    """
    
    def __init__(self, port: str = None, baudrate: int = None):
        """Инициализация детектора"""
        self.port = port or config.LIDAR_PORT
        self.baudrate = baudrate or config.LIDAR_BAUDRATE
        self.serial_conn = None
        self.logger = logging.getLogger(__name__)
        
        # Подключение к LiDAR
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1
            )
            self.logger.info(f"LiDAR подключен: {self.port}")
        except Exception as e:
            self.logger.error(f"Ошибка подключения LiDAR: {e}")
            raise
    
    def get_distances(self) -> List[float]:
        """
        Получить список расстояний от LiDAR
        
        Returns:
            Список расстояний в метрах
        """
        distances = []
        
        try:
            # Читаем данные в течение 0.2 секунды
            start_time = time.time()
            while time.time() - start_time < 0.2:
                # Ищем заголовок пакета (0x54)
                byte = self.serial_conn.read(1)
                if not byte or byte[0] != 0x54:
                    continue
                
                # Читаем остаток пакета (46 байт)
                packet = self.serial_conn.read(46)
                if len(packet) != 46:
                    continue
                
                # Парсим расстояния из пакета
                # Каждая точка: 2 байта расстояние + 1 байт интенсивность
                for i in range(12):  # 12 точек в пакете
                    offset = 4 + i * 3  # Данные начинаются с байта 4
                    if offset + 2 <= len(packet):
                        distance_mm = struct.unpack('<H', packet[offset:offset+2])[0]
                        distance_m = distance_mm / 1000.0
                        
                        # Фильтруем валидные расстояния
                        if 0.05 < distance_m < 10.0:
                            distances.append(distance_m)
        
        except Exception as e:
            self.logger.debug(f"Ошибка чтения LiDAR: {e}")
        
        return distances
    
    def detect_person(self) -> Optional[Tuple[float, float]]:
        """
        Обнаружить человека
        
        Returns:
            (x, y) позиция человека относительно робота или None
        """
        distances = self.get_distances()
        
        if not distances:
            return None
        
        # Ищем точки в диапазоне обнаружения человека (0.3 - 2.0 метра)
        person_distances = [d for d in distances if 0.2 <= d <= 0.5]
        
        if len(person_distances) < 3:  # Минимум 3 точки
            return None
        
        # Берем среднее расстояние
        avg_distance = sum(person_distances) / len(person_distances)
        
        # Возвращаем позицию (прямо перед роботом)
        # x - вперед, y - вбок (0 = прямо)
        x = avg_distance
        y = 0.0
        
        self.logger.debug(f"Человек обнаружен: {len(person_distances)} точек, расстояние {avg_distance:.2f}м")
        
        return (x, y)
    
    def close(self):
        """Закрыть соединение"""
        if self.serial_conn:
            self.serial_conn.close()
            self.logger.info("LiDAR отключен")


# Тест
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Упрощенный тест обнаружения человека")
    print("=" * 60)
    print()
    
    detector = SimplePersonDetector()
    
    print("Начало обнаружения (Ctrl+C для выхода)...")
    print()
    
    try:
        iteration = 0
        while True:
            iteration += 1
            
            distances = detector.get_distances()
            person = detector.detect_person()
            
            print(f"\r[{iteration:04d}] Точек: {len(distances):4d} | ", end="")
            
            if person:
                x, y = person
                print(f"ЧЕЛОВЕК ОБНАРУЖЕН! Расстояние: {x:.2f}м" + " " * 20, end="")
            else:
                print("Человек не обнаружен" + " " * 40, end="")
            
            time.sleep(0.2)
    
    except KeyboardInterrupt:
        print("\n\nОстановка...")
    finally:
        detector.close()
