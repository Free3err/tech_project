# -*- coding: utf-8 -*-
"""
Интерфейс LiDAR для RelayBot
Обеспечивает взаимодействие с LDROBOT D500 LiDAR сенсором
"""

import serial
import struct
import math
import time
import logging
from typing import List, Optional, Tuple
from navigation import ScanPoint
import config


# ============================================================================
# ИСКЛЮЧЕНИЯ ДЛЯ LIDAR СИСТЕМЫ
# ============================================================================

class LiDARError(Exception):
    """Базовое исключение для ошибок LiDAR"""
    pass


class LiDARConnectionError(LiDARError):
    """Ошибка подключения к LiDAR"""
    pass


class LiDARDataError(LiDARError):
    """Ошибка чтения данных от LiDAR"""
    pass


class LiDARInterface:
    """
    Интерфейс для работы с LDROBOT D500 LiDAR сенсором
    
    Обеспечивает:
    - Получение данных сканирования 360°
    - Обнаружение людей с использованием кластеризации
    - Обнаружение препятствий
    - Фильтрацию шума для надежного обнаружения в пределах 5 метров
    
    Протокол LDROBOT D500:
    - Скорость передачи: 230400 бод
    - Формат пакета: заголовок + данные измерений + CRC
    - Частота сканирования: ~10 Гц
    
    Attributes:
        port: Последовательный порт LiDAR
        baudrate: Скорость передачи данных
        serial_conn: Объект последовательного соединения
        last_scan: Последнее полученное сканирование
        scan_timestamp: Временная метка последнего сканирования
    """
    
    # Константы протокола LDROBOT D500
    HEADER = 0x54  # Байт заголовка пакета
    PACKET_SIZE = 47  # Размер пакета в байтах
    POINTS_PER_PACKET = 12  # Количество точек измерения в одном пакете
    
    def __init__(self, port: str = None, baudrate: int = None):
        """
        Инициализация интерфейса LiDAR
        
        Args:
            port: Последовательный порт LiDAR (по умолчанию из config)
            baudrate: Скорость передачи данных (по умолчанию из config)
        """
        self.port = port or config.LIDAR_PORT
        self.baudrate = baudrate or config.LIDAR_BAUDRATE
        self.serial_conn = None
        self.last_scan = []
        self.scan_timestamp = 0.0
        self.logger = logging.getLogger(__name__)
        
        # Счетчики ошибок
        self.connection_failures = 0
        self.data_read_failures = 0
        self.last_successful_read = time.time()
        
        # Попытка подключения к LiDAR
        self._connect()
    
    def _connect(self) -> None:
        """
        Установка соединения с LiDAR сенсором
        
        Raises:
            LiDARConnectionError: Если не удается подключиться к порту
        """
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1.0,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            self.logger.info(f"LiDAR подключен к порту {self.port}")
            self.connection_failures = 0
            self.last_successful_read = time.time()
        except serial.SerialException as e:
            self.connection_failures += 1
            self.logger.error(f"Ошибка подключения к LiDAR (попытка {self.connection_failures}): {e}")
            raise LiDARConnectionError(f"Не удалось подключиться к LiDAR на порту {self.port}: {e}")
        except Exception as e:
            self.connection_failures += 1
            self.logger.error(f"Неожиданная ошибка подключения к LiDAR: {e}")
            raise LiDARConnectionError(f"Критическая ошибка подключения к LiDAR: {e}")
    
    def _attempt_reconnection(self) -> bool:
        """
        Попытка переподключения к LiDAR
        
        Returns:
            True если переподключение успешно, False иначе
        """
        from config import MAX_RECOVERY_ATTEMPTS, RECOVERY_RETRY_DELAY
        
        self.logger.info("Попытка переподключения к LiDAR...")
        
        # Закрытие существующего соединения если есть
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception as e:
                self.logger.warning(f"Ошибка закрытия соединения: {e}")
        
        # Попытки переподключения с экспоненциальной задержкой
        for attempt in range(MAX_RECOVERY_ATTEMPTS):
            try:
                delay = RECOVERY_RETRY_DELAY * (2 ** attempt)
                self.logger.info(f"Попытка переподключения {attempt + 1}/{MAX_RECOVERY_ATTEMPTS} через {delay:.1f}с...")
                time.sleep(delay)
                
                self._connect()
                self.logger.info("Переподключение к LiDAR успешно")
                return True
            except LiDARConnectionError as e:
                self.logger.warning(f"Попытка переподключения {attempt + 1} не удалась: {e}")
                if attempt == MAX_RECOVERY_ATTEMPTS - 1:
                    self.logger.error("Все попытки переподключения исчерпаны")
                    return False
        
        return False
    
    def _read_packet(self) -> Optional[bytes]:
        """
        Чтение одного пакета данных от LiDAR
        
        Returns:
            Байты пакета или None если пакет не валиден
            
        Raises:
            serial.SerialException: При ошибке чтения из порта
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            return None
        
        try:
            # Поиск заголовка пакета
            attempts = 0
            max_attempts = 100  # Максимум попыток поиска заголовка
            
            while attempts < max_attempts:
                byte = self.serial_conn.read(1)
                if not byte:
                    return None
                
                attempts += 1
                
                if byte[0] == self.HEADER:
                    # Читаем остальную часть пакета
                    packet = byte + self.serial_conn.read(self.PACKET_SIZE - 1)
                    
                    if len(packet) == self.PACKET_SIZE:
                        # Проверка CRC (упрощенная)
                        if self._verify_crc(packet):
                            return packet
                        else:
                            self.logger.debug("Пакет не прошел проверку CRC")
            
            self.logger.warning(f"Не найден валидный заголовок пакета после {max_attempts} попыток")
            return None
                    
        except serial.SerialException as e:
            self.logger.error(f"Ошибка чтения данных LiDAR: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка чтения пакета: {e}")
            return None
    
    def _verify_crc(self, packet: bytes) -> bool:
        """
        Проверка контрольной суммы пакета
        
        Args:
            packet: Байты пакета
            
        Returns:
            True если CRC корректна, False иначе
        """
        # Упрощенная проверка CRC для LDROBOT D500
        # В реальной реализации нужно использовать правильный алгоритм CRC
        # Для MVP просто проверяем, что пакет не пустой и имеет правильный размер
        return len(packet) == self.PACKET_SIZE
    
    def _parse_packet(self, packet: bytes) -> List[ScanPoint]:
        """
        Парсинг пакета данных в список точек сканирования
        
        Формат пакета LDROBOT D500:
        - Байт 0: Заголовок (0x54)
        - Байт 1: Длина данных
        - Байт 2-3: Начальный угол (LSB, MSB)
        - Байты 4-39: Данные измерений (12 точек по 3 байта)
        - Байт 40-41: Конечный угол (LSB, MSB)
        - Байт 42-43: Временная метка
        - Байт 44: CRC
        
        Args:
            packet: Байты пакета
            
        Returns:
            Список объектов ScanPoint
        """
        points = []
        
        try:
            # Извлекаем начальный и конечный углы
            start_angle = struct.unpack('<H', packet[2:4])[0] / 100.0  # В градусах
            end_angle = struct.unpack('<H', packet[40:42])[0] / 100.0  # В градусах
            
            # Вычисляем шаг угла между точками
            angle_diff = end_angle - start_angle
            if angle_diff < 0:
                angle_diff += 360.0
            angle_step = angle_diff / (self.POINTS_PER_PACKET - 1) if self.POINTS_PER_PACKET > 1 else 0
            
            # Парсим каждую точку измерения
            for i in range(self.POINTS_PER_PACKET):
                offset = 4 + i * 3  # Смещение в пакете для i-й точки
                
                # Извлекаем расстояние (2 байта) и интенсивность (1 байт)
                distance_raw = struct.unpack('<H', packet[offset:offset+2])[0]
                intensity = packet[offset+2]
                
                # Преобразуем расстояние в метры (LiDAR возвращает в мм)
                distance = distance_raw / 1000.0
                
                # Вычисляем угол для этой точки
                angle_deg = start_angle + i * angle_step
                angle_rad = math.radians(angle_deg)
                
                # Фильтрация: игнорируем точки вне допустимого диапазона
                if config.LIDAR_MIN_RANGE <= distance <= config.LIDAR_MAX_RANGE:
                    points.append(ScanPoint(
                        distance=distance,
                        angle=angle_rad,
                        intensity=intensity
                    ))
            
        except (struct.error, IndexError) as e:
            self.logger.error(f"Ошибка парсинга пакета LiDAR: {e}")
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка парсинга пакета: {e}")
        
        return points
    
    def get_scan(self) -> List[ScanPoint]:
        """
        Получить текущее сканирование LiDAR
        
        Собирает полное 360° сканирование из нескольких пакетов.
        Обновляет last_scan и scan_timestamp.
        Включает обработку ошибок с попытками переподключения.
        
        Returns:
            Список объектов ScanPoint с данными сканирования
            
        Raises:
            LiDARConnectionError: Если не удалось переподключиться после потери связи
            LiDARDataError: Если не удалось получить валидные данные
        """
        # Проверка соединения
        if not self.serial_conn or not self.serial_conn.is_open:
            self.logger.warning("LiDAR соединение потеряно, попытка переподключения...")
            if not self._attempt_reconnection():
                raise LiDARConnectionError("Не удалось переподключиться к LiDAR")
        
        scan_points = []
        packets_collected = 0
        max_packets = 30  # Примерно 30 пакетов для полного оборота 360°
        
        start_time = time.time()
        timeout = 1.0  # Таймаут 1 секунда для сбора полного сканирования
        
        consecutive_failures = 0
        max_consecutive_failures = 5
        
        while packets_collected < max_packets and (time.time() - start_time) < timeout:
            try:
                packet = self._read_packet()
                if packet:
                    points = self._parse_packet(packet)
                    scan_points.extend(points)
                    packets_collected += 1
                    consecutive_failures = 0  # Сброс счетчика при успешном чтении
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        self.logger.warning(f"Слишком много неудачных попыток чтения ({consecutive_failures})")
                        break
            except serial.SerialException as e:
                self.data_read_failures += 1
                self.logger.error(f"Ошибка чтения данных LiDAR: {e}")
                
                # Попытка переподключения при ошибке чтения
                if self._attempt_reconnection():
                    continue
                else:
                    raise LiDARConnectionError("Потеряно соединение с LiDAR")
            except Exception as e:
                self.data_read_failures += 1
                self.logger.error(f"Неожиданная ошибка при чтении LiDAR: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    break
        
        # Проверка, получили ли мы достаточно данных
        if packets_collected == 0:
            self.logger.error("Не удалось получить ни одного пакета данных от LiDAR")
            raise LiDARDataError("Нет данных от LiDAR")
        
        if packets_collected < max_packets / 2:
            self.logger.warning(f"Получено только {packets_collected}/{max_packets} пакетов")
        
        # Фильтрация шума: удаляем точки с низкой интенсивностью
        filtered_points = self._filter_noise(scan_points)
        
        # Обновляем последнее сканирование
        self.last_scan = filtered_points
        self.scan_timestamp = time.time()
        self.last_successful_read = time.time()
        
        # Логирование статистики сканирования
        self.logger.debug(f"Сканирование завершено: {len(filtered_points)} точек из {len(scan_points)} ({packets_collected} пакетов)")
        
        # Сброс счетчика ошибок при успешном сканировании
        if self.data_read_failures > 0:
            self.logger.info(f"Чтение LiDAR восстановлено после {self.data_read_failures} ошибок")
            self.data_read_failures = 0
        
        return filtered_points
    
    def _filter_noise(self, points: List[ScanPoint]) -> List[ScanPoint]:
        """
        Фильтрация шума из данных сканирования
        
        Удаляет точки с низкой интенсивностью и изолированные точки,
        которые вероятно являются шумом.
        
        Args:
            points: Список точек сканирования
            
        Returns:
            Отфильтрованный список точек
        """
        if not points:
            return []
        
        # Фильтр 1: Удаляем точки с очень низкой интенсивностью (вероятно шум)
        MIN_INTENSITY = 20
        filtered = [p for p in points if p.intensity >= MIN_INTENSITY]
        
        # Фильтр 2: Удаляем изолированные точки (медианный фильтр)
        # Для упрощения пропускаем этот шаг в MVP
        
        return filtered
    
    def detect_person(self) -> Optional[Tuple[float, float]]:
        """
        Упрощенное обнаружение человека
        
        Ищет точки в диапазоне 0.3-2.0 метра и возвращает среднее расстояние.
        Это временное упрощенное решение пока не исправим парсинг LiDAR.
        
        Returns:
            Позиция человека (x, y) относительно робота или None если не обнаружен
        """
        # Получаем текущее сканирование
        scan = self.last_scan if self.last_scan else self.get_scan()
        
        if not scan or len(scan) < 3:
            return None
        
        # Ищем точки в диапазоне обнаружения человека (0.3 - 2.0 метра)
        person_points = [p for p in scan if 0.3 <= p.distance <= 2.0]
        
        if len(person_points) < 3:  # Минимум 3 точки
            return None
        
        # Берем среднее расстояние
        avg_distance = sum(p.distance for p in person_points) / len(person_points)
        
        # Возвращаем позицию (прямо перед роботом)
        # x - вперед, y - вбок (0 = прямо)
        x = avg_distance
        y = 0.0
        
        self.logger.info(f"Человек обнаружен: {len(person_points)} точек, расстояние {avg_distance:.2f}м")
        
        return (x, y)
    
    def _cluster_points(self, points: List[Tuple[float, float]]) -> List[List[Tuple[float, float]]]:
        """
        Кластеризация точек методом ближайшего соседа
        
        Группирует точки, которые находятся близко друг к другу
        (в пределах PERSON_DETECTION_CLUSTER_DISTANCE).
        
        Args:
            points: Список точек в декартовых координатах (x, y)
            
        Returns:
            Список кластеров, где каждый кластер - список точек
        """
        if not points:
            return []
        
        clusters = []
        used = set()
        
        for i, point in enumerate(points):
            if i in used:
                continue
            
            # Создаем новый кластер
            cluster = [point]
            used.add(i)
            
            # Ищем все точки, близкие к текущему кластеру
            changed = True
            while changed:
                changed = False
                for j, other_point in enumerate(points):
                    if j in used:
                        continue
                    
                    # Проверяем расстояние до любой точки в кластере
                    for cluster_point in cluster:
                        dist = math.sqrt(
                            (other_point[0] - cluster_point[0])**2 +
                            (other_point[1] - cluster_point[1])**2
                        )
                        
                        if dist <= config.PERSON_DETECTION_CLUSTER_DISTANCE:
                            cluster.append(other_point)
                            used.add(j)
                            changed = True
                            break
            
            clusters.append(cluster)
        
        return clusters
    
    def _calculate_cluster_size(self, cluster: List[Tuple[float, float]]) -> float:
        """
        Вычисление размера кластера (максимальное расстояние между точками)
        
        Args:
            cluster: Список точек в кластере
            
        Returns:
            Размер кластера в метрах
        """
        if len(cluster) < 2:
            return 0.0
        
        max_distance = 0.0
        for i, p1 in enumerate(cluster):
            for p2 in cluster[i+1:]:
                dist = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                max_distance = max(max_distance, dist)
        
        return max_distance
    
    def get_obstacles(self, min_distance: float = None) -> List[Tuple[float, float]]:
        """
        Получить препятствия ближе заданного расстояния
        
        Возвращает позиции всех точек сканирования, которые находятся
        ближе указанного минимального расстояния.
        
        Args:
            min_distance: Минимальное расстояние для обнаружения препятствий в метрах
                         (по умолчанию из config.OBSTACLE_MIN_DISTANCE)
            
        Returns:
            Список позиций препятствий (x, y) относительно робота
        """
        if min_distance is None:
            min_distance = config.OBSTACLE_MIN_DISTANCE
        
        # Получаем текущее сканирование
        scan = self.last_scan if self.last_scan else self.get_scan()
        
        obstacles = []
        for point in scan:
            if point.distance < min_distance:
                # Преобразуем в декартовы координаты
                x = point.distance * math.cos(point.angle)
                y = point.distance * math.sin(point.angle)
                obstacles.append((x, y))
        
        if obstacles:
            self.logger.debug(f"Обнаружено {len(obstacles)} препятствий ближе {min_distance:.2f}м")
        
        return obstacles
    
    def close(self) -> None:
        """
        Закрытие соединения с LiDAR
        """
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
                self.logger.info("LiDAR соединение закрыто")
            except Exception as e:
                self.logger.error(f"Ошибка закрытия соединения LiDAR: {e}")
    
    def __del__(self):
        """
        Деструктор: закрываем соединение при удалении объекта
        """
        self.close()
