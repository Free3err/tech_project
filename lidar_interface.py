# -*- coding: utf-8 -*-
import serial
import math
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
        self.buf = bytearray()
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
        points = []
        
        try:
            self.buf.extend(self.serial_conn.read(2000))
            
            while len(self.buf) >= 47:
                if self.buf[0] == 0x54 and self.buf[1] == 0x2C:
                    packet = self.buf[:47]
                    del self.buf[:47]
                    
                    start_angle = int.from_bytes(packet[4:6], 'little') / 100.0
                    end_angle = int.from_bytes(packet[42:44], 'little') / 100.0
                    
                    angle_diff = (end_angle - start_angle + 360) % 360
                    step = angle_diff / 11
                    
                    for i in range(12):
                        dist_mm = int.from_bytes(packet[6 + i * 3: 8 + i * 3], 'little')
                        conf = packet[8 + i * 3]
                        
                        if dist_mm > 0:
                            dist_m = dist_mm / 1000.0
                            angle_deg = start_angle + i * step
                            angle_rad = math.radians(angle_deg)
                            
                            if config.LIDAR_MIN_RANGE < dist_m < config.LIDAR_MAX_RANGE:
                                points.append(ScanPoint(dist_m, angle_rad, conf))
                else:
                    self.buf.pop(0)
        
        except Exception as e:
            self.logger.debug(f"Ошибка чтения LiDAR: {e}")
        
        return points
    
    def detect_person(self) -> Optional[Tuple[float, float]]:
        scan = self.get_scan()
        
        if len(scan) < 3:
            return None
        
        avg_distance = sum(p.distance for p in scan) / len(scan)
        
        # Проверка диапазона обнаружения человека
        if avg_distance < config.LIDAR_MIN_RANGE or avg_distance > config.LIDAR_MAX_RANGE:
            return None
        
        x = avg_distance * math.cos(0)
        y = avg_distance * math.sin(0)
        
        self.logger.info(f"Обнаружено {len(scan)} точек, расстояние {avg_distance:.2f}м")
        
        return (x, y)
    
    def get_obstacles(self, min_distance: float) -> List[Tuple[float, float]]:
        scan = self.get_scan()
        obstacles = []
        
        for point in scan:
            if point.distance < min_distance:
                x = point.distance * math.cos(point.angle)
                y = point.distance * math.sin(point.angle)
                obstacles.append((x, y))
        
        return obstacles
    
    def close(self):
        if self.serial_conn:
            self.serial_conn.close()
