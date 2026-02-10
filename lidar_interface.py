# -*- coding: utf-8 -*-
import serial
import struct
import logging
from typing import Optional, Tuple, List
from navigation import ScanPoint
import config


class LiDARInterface:
    def __init__(self, port: str = None, baudrate: int = None):
        self.port = port or config.LIDAR_PORT
        self.baudrate = baudrate or config.LIDAR_BAUDRATE
        self.serial_conn = None
        self.logger = logging.getLogger(__name__)
        self._connect()
    
    def _connect(self) -> None:
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
    
    def get_scan(self) -> List[ScanPoint]:
        """Получить сканирование LiDAR"""
        points = []
        
        try:
            # Читаем несколько пакетов
            for _ in range(10):
                byte = self.serial_conn.read(1)
                if not byte or byte[0] != 0x54:
                    continue
                
                packet = self.serial_conn.read(46)
                if len(packet) != 46:
                    continue
                
                # Парсим точки из пакета
                for i in range(12):
                    offset = 4 + i * 3
                    if offset + 2 <= len(packet):
                        distance_mm = struct.unpack('<H', packet[offset:offset+2])[0]
                        distance_m = distance_mm / 1000.0
                        intensity = packet[offset+2]
                        
                        if config.LIDAR_MIN_RANGE < distance_m < config.LIDAR_MAX_RANGE:
                            points.append(ScanPoint(distance_m, 0.0, intensity))
        
        except Exception as e:
            self.logger.debug(f"Ошибка чтения LiDAR: {e}")
        
        return points
    
    def detect_person(self) -> Optional[Tuple[float, float]]:
        """Обнаружить человека - просто ищем близкие точки"""
        scan = self.get_scan()
        
        if len(scan) < 3:
            return None
        
        # Берем среднее расстояние всех точек
        avg_distance = sum(p.distance for p in scan) / len(scan)
        
        self.logger.info(f"Обнаружено {len(scan)} точек, среднее расстояние {avg_distance:.2f}м")
        
        return (avg_distance, 0.0)
    
    def get_obstacles(self, min_distance: float) -> List[Tuple[float, float]]:
        """Получить препятствия ближе min_distance"""
        scan = self.get_scan()
        obstacles = []
        
        for point in scan:
            if point.distance < min_distance:
                obstacles.append((point.distance, 0.0))
        
        return obstacles
    
    def close(self):
        if self.serial_conn:
            self.serial_conn.close()
