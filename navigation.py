"""
Модуль навигации для RelayBot
Содержит структуры данных и систему навигации для автономного робота доставки
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
import numpy as np
import yaml
import logging
import math
import heapq
import time
from collections import defaultdict


# ============================================================================
# ИСКЛЮЧЕНИЯ ДЛЯ НАВИГАЦИОННОЙ СИСТЕМЫ
# ============================================================================

class NavigationError(Exception):
    """Базовое исключение для ошибок навигации"""
    pass


class LocalizationFailureError(NavigationError):
    """Ошибка локализации (расхождение фильтра частиц)"""
    pass


class PathPlanningFailureError(NavigationError):
    """Ошибка планирования пути (не найден валидный путь)"""
    pass


class GoalUnreachableError(NavigationError):
    """Цель недостижима (обнаружено застревание)"""
    pass


class ObstacleCollisionError(NavigationError):
    """Столкновение с препятствием (экстренная остановка IR сенсора)"""
    pass


@dataclass
class Position:
    """
    Позиция робота в глобальных координатах
    
    Attributes:
        x: Координата X в метрах
        y: Координата Y в метрах
        theta: Ориентация в радианах (0 = направление на восток)
    """
    x: float
    y: float
    theta: float


@dataclass
class ScanPoint:
    """
    Точка LiDAR сканирования
    
    Attributes:
        distance: Расстояние до объекта в метрах
        angle: Угол в радианах (относительно направления робота)
        intensity: Интенсивность отражения (0-255)
    """
    distance: float
    angle: float
    intensity: int


@dataclass
class Waypoint:
    """
    Точка маршрута для навигации
    
    Attributes:
        x: Координата X целевой точки в метрах
        y: Координата Y целевой точки в метрах
        tolerance: Допуск достижения точки в метрах (по умолчанию 0.1м)
    """
    x: float
    y: float
    tolerance: float = 0.1


@dataclass
class StateContext:
    """
    Контекст состояния машины состояний
    Хранит информацию о текущей позиции, целях и заказе
    
    Attributes:
        current_position: Текущая позиция робота
        target_position: Целевая позиция для навигации (может быть None)
        customer_position: Сохраненная позиция клиента для возврата (может быть None)
        current_order_id: ID текущего заказа (может быть None)
        error_message: Сообщение об ошибке (может быть None)
    """
    current_position: Position
    target_position: Optional[Position] = None
    customer_position: Optional[Position] = None
    current_order_id: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class Particle:
    """
    Частица для фильтра частиц (локализация)
    
    Attributes:
        x: Координата X в метрах
        y: Координата Y в метрах
        theta: Ориентация в радианах
        weight: Вес частицы (вероятность)
    """
    x: float
    y: float
    theta: float
    weight: float = 1.0


class NavigationSystem:
    """
    Система навигации для автономного робота
    Обеспечивает локализацию, планирование пути и управление движением
    """
    
    def __init__(self, map_file: str, lidar_interface, odometry, serial_comm):
        """
        Инициализация системы навигации
        
        Args:
            map_file: Путь к файлу карты окружения (YAML)
            lidar_interface: Интерфейс LiDAR сенсора
            odometry: Система одометрии
            serial_comm: Связь с Arduino для управления моторами
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Инициализация системы навигации")
        
        # Сохранение ссылок на подсистемы
        self.lidar = lidar_interface
        self.odometry = odometry
        self.serial = serial_comm
        
        # Загрузка карты окружения
        self.map_data = self._load_map(map_file)
        self.occupancy_grid = self._create_occupancy_grid()
        
        # Инициализация фильтра частиц для локализации
        self.particles = self._initialize_particles()
        
        # Текущая оценка позиции
        self.current_position = Position(0.0, 0.0, 0.0)
        
        # Флаг остановки
        self.is_stopped = True
        
        # Счетчики ошибок для обработки
        self.path_planning_failures = 0
        self.localization_failures = 0
        self.stuck_detections = 0
        
        # Время последней успешной локализации
        self.last_successful_localization = time.time()
        
        self.logger.info("Система навигации инициализирована")
    
    def _load_map(self, map_file: str) -> dict:
        """
        Загрузка карты из YAML файла
        
        Args:
            map_file: Путь к файлу карты
            
        Returns:
            Словарь с данными карты
        """
        try:
            with open(map_file, 'r', encoding='utf-8') as f:
                map_data = yaml.safe_load(f)
            self.logger.info(f"Карта загружена из {map_file}")
            return map_data
        except Exception as e:
            self.logger.error(f"Ошибка загрузки карты: {e}")
            # Возвращаем карту по умолчанию
            return {
                'width': 10.0,
                'height': 10.0,
                'resolution': 0.05,
                'origin': {'x': -2.0, 'y': -2.0},
                'obstacles': []
            }
    
    def _create_occupancy_grid(self) -> np.ndarray:
        """
        Создание сетки занятости из данных карты
        
        Returns:
            2D массив numpy (0 = свободно, 1 = занято)
        """
        width = self.map_data['width']
        height = self.map_data['height']
        resolution = self.map_data['resolution']
        
        # Размер сетки в пикселях
        grid_width = int(width / resolution)
        grid_height = int(height / resolution)
        
        # Создание пустой сетки
        grid = np.zeros((grid_height, grid_width), dtype=np.uint8)
        
        # Заполнение препятствий
        origin_x = self.map_data['origin']['x']
        origin_y = self.map_data['origin']['y']
        
        for obstacle in self.map_data.get('obstacles', []):
            if obstacle['type'] == 'rectangle':
                # Преобразование координат в индексы сетки
                x1 = int((obstacle['x'] - origin_x) / resolution)
                y1 = int((obstacle['y'] - origin_y) / resolution)
                x2 = int((obstacle['x'] + obstacle['width'] - origin_x) / resolution)
                y2 = int((obstacle['y'] + obstacle['height'] - origin_y) / resolution)
                
                # Ограничение индексов границами сетки
                x1 = max(0, min(x1, grid_width - 1))
                y1 = max(0, min(y1, grid_height - 1))
                x2 = max(0, min(x2, grid_width - 1))
                y2 = max(0, min(y2, grid_height - 1))
                
                # Заполнение прямоугольника
                grid[y1:y2, x1:x2] = 1
        
        self.logger.info(f"Создана сетка занятости {grid_width}x{grid_height}")
        return grid
    
    def _initialize_particles(self) -> List[Particle]:
        """
        Инициализация частиц для фильтра частиц
        Частицы распределяются вокруг начальной позиции (0, 0)
        
        Returns:
            Список частиц
        """
        from config import NUM_PARTICLES, MOTION_NOISE_TRANSLATION, MOTION_NOISE_ROTATION
        
        particles = []
        for _ in range(NUM_PARTICLES):
            # Начальное распределение вокруг (0, 0) с небольшим шумом
            x = np.random.normal(0.0, MOTION_NOISE_TRANSLATION * 2)
            y = np.random.normal(0.0, MOTION_NOISE_TRANSLATION * 2)
            theta = np.random.uniform(0, 2 * np.pi)
            particles.append(Particle(x, y, theta, 1.0 / NUM_PARTICLES))
        
        self.logger.info(f"Инициализировано {NUM_PARTICLES} частиц")
        return particles
    
    def get_current_position(self) -> Tuple[float, float, float]:
        """
        Получить текущую позицию робота
        
        Returns:
            Кортеж (x, y, theta) в глобальных координатах
        """
        return (self.current_position.x, self.current_position.y, self.current_position.theta)
    
    def stop(self) -> None:
        """
        Экстренная остановка робота
        Останавливает все моторы немедленно
        """
        self.logger.warning("Экстренная остановка")
        self.is_stopped = True
        
        # Отправка команды остановки моторам
        try:
            self.serial.send_motor_command(0, 0, 0, 0)
        except Exception as e:
            self.logger.error(f"Ошибка отправки команды остановки: {e}")
    
    def _check_ir_sensor_emergency_stop(self) -> bool:
        """
        Проверка IR сенсора на наличие препятствий для экстренной остановки
        
        Returns:
            True если обнаружено препятствие требующее экстренной остановки, False иначе
            
        Raises:
            ObstacleCollisionError: Если обнаружено критическое препятствие
        """
        from config import IR_EMERGENCY_STOP_DISTANCE
        
        try:
            # Чтение данных IR сенсора
            sensor_data = self.serial.read_sensor_data()
            
            if sensor_data and 'ir' in sensor_data:
                ir_distance = sensor_data['ir'] / 100.0  # Преобразование см в метры
                
                if ir_distance < IR_EMERGENCY_STOP_DISTANCE:
                    self.logger.error(f"Обнаружено препятствие на расстоянии {ir_distance:.2f}м - экстренная остановка!")
                    self.stop()
                    raise ObstacleCollisionError(
                        f"Критическое препятствие на расстоянии {ir_distance:.2f}м"
                    )
                
                return False
        except ObstacleCollisionError:
            # Пробрасываем ошибку столкновения дальше
            raise
        except Exception as e:
            self.logger.warning(f"Ошибка чтения IR сенсора: {e}")
            # Не критическая ошибка, продолжаем работу
            return False
        
        return False

    
    def update_localization(self) -> None:
        """
        Обновление локализации с использованием фильтра частиц
        Интегрирует данные одометрии и LiDAR для оценки позиции
        
        Алгоритм:
        1. Предсказание движения на основе одометрии
        2. Обновление весов частиц на основе LiDAR сканирования
        3. Ресемплинг частиц
        4. Оценка текущей позиции
        
        Raises:
            LocalizationFailureError: Если обнаружено расхождение локализации
        """
        from config import (MOTION_NOISE_TRANSLATION, MOTION_NOISE_ROTATION,
                           MEASUREMENT_NOISE, RESAMPLE_THRESHOLD)
        
        try:
            # Шаг 1: Предсказание движения на основе одометрии
            odom_x, odom_y, odom_theta = self.odometry.get_pose()
            
            # Вычисление изменения позиции с предыдущего обновления
            delta_x = odom_x - self.current_position.x
            delta_y = odom_y - self.current_position.y
            delta_theta = self._normalize_angle(odom_theta - self.current_position.theta)
            
            # Применение движения к каждой частице с шумом
            for particle in self.particles:
                # Добавление шума к движению
                noisy_dx = delta_x + np.random.normal(0, MOTION_NOISE_TRANSLATION)
                noisy_dy = delta_y + np.random.normal(0, MOTION_NOISE_TRANSLATION)
                noisy_dtheta = delta_theta + np.random.normal(0, MOTION_NOISE_ROTATION)
                
                # Обновление позиции частицы
                particle.x += noisy_dx
                particle.y += noisy_dy
                particle.theta = self._normalize_angle(particle.theta + noisy_dtheta)
            
            # Шаг 2: Обновление весов на основе LiDAR сканирования
            lidar_scan = self.lidar.get_scan()
            
            if lidar_scan and len(lidar_scan) > 0:
                for particle in self.particles:
                    # Вычисление вероятности наблюдения для этой частицы
                    likelihood = self._compute_scan_likelihood(particle, lidar_scan)
                    particle.weight *= likelihood
                
                # Нормализация весов
                total_weight = sum(p.weight for p in self.particles)
                if total_weight > 0:
                    for particle in self.particles:
                        particle.weight /= total_weight
                else:
                    # Если все веса нулевые, сброс к равномерному распределению
                    for particle in self.particles:
                        particle.weight = 1.0 / len(self.particles)
            
            # Шаг 3: Ресемплинг при необходимости
            effective_particles = self._compute_effective_particles()
            if effective_particles < RESAMPLE_THRESHOLD * len(self.particles):
                self._resample_particles()
            
            # Шаг 4: Оценка текущей позиции (взвешенное среднее)
            self._estimate_position()
            
            # Проверка здоровья локализации
            if not self._check_localization_health():
                self._handle_localization_failure()
            else:
                # Обновление времени последней успешной локализации
                self.last_successful_localization = time.time()
                # Сброс счетчика ошибок при успешной локализации
                if self.localization_failures > 0:
                    self.logger.info("Локализация восстановлена")
                    self.localization_failures = 0
            
        except LocalizationFailureError:
            # Пробрасываем ошибку локализации дальше
            raise
        except Exception as e:
            self.logger.error(f"Ошибка обновления локализации: {e}")
            raise LocalizationFailureError(f"Критическая ошибка локализации: {e}")
    
    def _normalize_angle(self, angle: float) -> float:
        """
        Нормализация угла в диапазон [-pi, pi]
        
        Args:
            angle: Угол в радианах
            
        Returns:
            Нормализованный угол
        """
        while angle > np.pi:
            angle -= 2 * np.pi
        while angle < -np.pi:
            angle += 2 * np.pi
        return angle
    
    def _compute_scan_likelihood(self, particle: Particle, scan: List[Tuple[float, float]]) -> float:
        """
        Вычисление вероятности наблюдения LiDAR сканирования для данной частицы
        
        Args:
            particle: Частица с позицией
            scan: Список точек сканирования (расстояние, угол)
            
        Returns:
            Вероятность наблюдения (0-1)
        """
        from config import MEASUREMENT_NOISE
        
        # Упрощенная модель: сравнение ожидаемых расстояний с наблюдаемыми
        # Для каждой точки сканирования вычисляем ожидаемое расстояние до препятствия
        
        likelihood = 1.0
        sample_size = min(len(scan), 12)  # Уменьшено до 12 для производительности
        step = len(scan) // sample_size if sample_size > 0 else 1
        
        for i in range(0, len(scan), step):
            # scan[i] это объект ScanPoint с полями distance, angle, intensity
            scan_point = scan[i]
            distance = scan_point.distance
            angle = scan_point.angle
            
            # Вычисление глобального угла луча
            global_angle = self._normalize_angle(particle.theta + angle)
            
            # Вычисление ожидаемого расстояния до препятствия
            expected_distance = self._ray_cast(particle.x, particle.y, global_angle)
            
            # Вычисление вероятности на основе разницы расстояний
            if expected_distance > 0:
                diff = abs(distance - expected_distance)
                prob = np.exp(-0.5 * (diff / MEASUREMENT_NOISE) ** 2)
                likelihood *= prob
        
        return max(likelihood, 1e-10)  # Избегаем нулевой вероятности
    
    def _ray_cast(self, x: float, y: float, angle: float, max_range: float = 10.0) -> float:
        """
        Трассировка луча для определения расстояния до препятствия
        
        Args:
            x: Координата X начала луча
            y: Координата Y начала луча
            angle: Угол луча в радианах
            max_range: Максимальная дальность луча
            
        Returns:
            Расстояние до препятствия (или max_range если не найдено)
        """
        resolution = self.map_data['resolution']
        origin_x = self.map_data['origin']['x']
        origin_y = self.map_data['origin']['y']
        
        # Шаг трассировки
        step = resolution / 2
        
        # Направление луча
        dx = np.cos(angle) * step
        dy = np.sin(angle) * step
        
        # Трассировка луча
        current_x = x
        current_y = y
        distance = 0.0
        
        while distance < max_range:
            # Преобразование в индексы сетки
            grid_x = int((current_x - origin_x) / resolution)
            grid_y = int((current_y - origin_y) / resolution)
            
            # Проверка границ
            if (grid_x < 0 or grid_x >= self.occupancy_grid.shape[1] or
                grid_y < 0 or grid_y >= self.occupancy_grid.shape[0]):
                return max_range
            
            # Проверка препятствия
            if self.occupancy_grid[grid_y, grid_x] == 1:
                return distance
            
            # Продвижение луча
            current_x += dx
            current_y += dy
            distance += step
        
        return max_range
    
    def _compute_effective_particles(self) -> float:
        """
        Вычисление эффективного количества частиц
        
        Returns:
            Эффективное количество частиц
        """
        sum_weights_squared = sum(p.weight ** 2 for p in self.particles)
        if sum_weights_squared > 0:
            return 1.0 / sum_weights_squared
        return 0.0
    
    def _resample_particles(self) -> None:
        """
        Ресемплинг частиц на основе их весов
        Использует алгоритм низкодисперсионного ресемплинга
        """
        from config import NUM_PARTICLES
        
        # Создание кумулятивного распределения весов
        cumulative_weights = []
        cumulative_sum = 0.0
        for particle in self.particles:
            cumulative_sum += particle.weight
            cumulative_weights.append(cumulative_sum)
        
        # Низкодисперсионный ресемплинг
        new_particles = []
        step = 1.0 / NUM_PARTICLES
        start = np.random.uniform(0, step)
        
        for i in range(NUM_PARTICLES):
            target = start + i * step
            
            # Поиск частицы для копирования
            for j, cum_weight in enumerate(cumulative_weights):
                if target <= cum_weight:
                    old_particle = self.particles[j]
                    new_particle = Particle(
                        old_particle.x,
                        old_particle.y,
                        old_particle.theta,
                        1.0 / NUM_PARTICLES
                    )
                    new_particles.append(new_particle)
                    break
        
        self.particles = new_particles
        self.logger.debug("Выполнен ресемплинг частиц")
    
    def _estimate_position(self) -> None:
        """
        Оценка текущей позиции на основе взвешенного среднего частиц
        """
        # Взвешенное среднее для x и y
        x = sum(p.x * p.weight for p in self.particles)
        y = sum(p.y * p.weight for p in self.particles)
        
        # Для угла используем круговое среднее
        sin_sum = sum(np.sin(p.theta) * p.weight for p in self.particles)
        cos_sum = sum(np.cos(p.theta) * p.weight for p in self.particles)
        theta = np.arctan2(sin_sum, cos_sum)
        
        self.current_position = Position(x, y, theta)
    
    def _check_localization_health(self) -> bool:
        """
        Проверка здоровья системы локализации
        
        Проверяет расхождение фильтра частиц по дисперсии позиций частиц.
        Если дисперсия слишком велика, локализация считается неудачной.
        
        Returns:
            True если локализация здорова, False если обнаружено расхождение
        """
        from config import POSITION_TOLERANCE
        
        # Вычисление дисперсии позиций частиц
        mean_x = sum(p.x * p.weight for p in self.particles)
        mean_y = sum(p.y * p.weight for p in self.particles)
        
        variance_x = sum(p.weight * (p.x - mean_x)**2 for p in self.particles)
        variance_y = sum(p.weight * (p.y - mean_y)**2 for p in self.particles)
        
        # Стандартное отклонение
        std_dev = np.sqrt(variance_x + variance_y)
        
        # Порог расхождения: если стандартное отклонение больше 1 метра,
        # считаем что локализация расходится
        divergence_threshold = 1.0
        
        if std_dev > divergence_threshold:
            self.logger.warning(f"Обнаружено расхождение локализации: std_dev={std_dev:.2f}м")
            return False
        
        # Проверка эффективного количества частиц
        effective_particles = self._compute_effective_particles()
        min_effective_particles = len(self.particles) * 0.1  # Минимум 10% эффективных частиц
        
        if effective_particles < min_effective_particles:
            self.logger.warning(f"Низкое эффективное количество частиц: {effective_particles:.1f}")
            return False
        
        return True
    
    def _attempt_relocalization(self) -> bool:
        """
        Попытка повторной локализации при расхождении фильтра частиц
        
        Переинициализирует частицы вокруг текущей оценки позиции
        с большим разбросом для восстановления локализации.
        
        Returns:
            True если релокализация успешна, False иначе
        """
        from config import NUM_PARTICLES, MOTION_NOISE_TRANSLATION
        
        self.logger.info("Попытка релокализации...")
        
        # Сохранение текущей оценки позиции
        current_x = self.current_position.x
        current_y = self.current_position.y
        current_theta = self.current_position.theta
        
        # Переинициализация частиц с большим разбросом
        self.particles = []
        for _ in range(NUM_PARTICLES):
            # Разброс 0.5 метра вокруг текущей позиции
            x = np.random.normal(current_x, 0.5)
            y = np.random.normal(current_y, 0.5)
            theta = np.random.uniform(0, 2 * np.pi)
            self.particles.append(Particle(x, y, theta, 1.0 / NUM_PARTICLES))
        
        # Выполнение нескольких итераций обновления локализации
        for _ in range(5):
            try:
                self.update_localization()
            except Exception as e:
                self.logger.error(f"Ошибка при релокализации: {e}")
                return False
        
        # Проверка успешности релокализации
        if self._check_localization_health():
            self.logger.info("Релокализация успешна")
            self.localization_failures = 0
            self.last_successful_localization = time.time()
            return True
        else:
            self.logger.warning("Релокализация не удалась")
            return False
    
    def _handle_localization_failure(self) -> None:
        """
        Обработка ошибки локализации с попытками восстановления
        
        Raises:
            LocalizationFailureError: Если не удалось восстановить локализацию
        """
        from config import MAX_RECOVERY_ATTEMPTS, RECOVERY_RETRY_DELAY
        
        self.localization_failures += 1
        self.logger.error(f"Ошибка локализации (попытка {self.localization_failures})")
        
        # Попытки релокализации с экспоненциальной задержкой
        for attempt in range(MAX_RECOVERY_ATTEMPTS):
            self.logger.info(f"Попытка релокализации {attempt + 1}/{MAX_RECOVERY_ATTEMPTS}")
            
            # Экспоненциальная задержка
            delay = RECOVERY_RETRY_DELAY * (2 ** attempt)
            time.sleep(delay)
            
            # Попытка релокализации
            if self._attempt_relocalization():
                return
        
        # Если все попытки неудачны, выбрасываем исключение
        raise LocalizationFailureError(
            f"Не удалось восстановить локализацию после {MAX_RECOVERY_ATTEMPTS} попыток"
        )

    def plan_path(self, start: Tuple[float, float], goal: Tuple[float, float]) -> List[Tuple[float, float]]:
        """
        Планирование пути от начальной до целевой точки с использованием A*
        
        Args:
            start: Начальная позиция (x, y) в метрах
            goal: Целевая позиция (x, y) в метрах
            
        Returns:
            Список точек пути [(x1, y1), (x2, y2), ...] или пустой список если путь не найден
            
        Raises:
            PathPlanningFailureError: Если не удалось спланировать путь после нескольких попыток
        """
        from config import (OBSTACLE_CLEARANCE, PLANNING_STEP_SIZE, 
                           MAX_PLANNING_ITERATIONS, POSITION_TOLERANCE,
                           MAX_RECOVERY_ATTEMPTS, RECOVERY_RETRY_DELAY)
        
        self.logger.info(f"Планирование пути от {start} до {goal}")
        
        # Проверка валидности начальной и конечной точек
        if not self._is_valid_position(start[0], start[1]):
            self.logger.error(f"Начальная позиция {start} невалидна (препятствие)")
            # Попытка найти ближайшую валидную позицию
            start = self._find_nearest_valid_position(start[0], start[1])
            if start is None:
                raise PathPlanningFailureError("Не удалось найти валидную начальную позицию")
            self.logger.info(f"Использую ближайшую валидную начальную позицию: {start}")
        
        if not self._is_valid_position(goal[0], goal[1]):
            self.logger.error(f"Целевая позиция {goal} невалидна (препятствие)")
            # Попытка найти ближайшую валидную позицию
            goal = self._find_nearest_valid_position(goal[0], goal[1])
            if goal is None:
                raise PathPlanningFailureError("Не удалось найти валидную целевую позицию")
            self.logger.info(f"Использую ближайшую валидную целевую позицию: {goal}")
        
        # Если начало и цель совпадают, возвращаем путь из одной точки
        if self._distance(start, goal) < POSITION_TOLERANCE:
            self.logger.info("Начало и цель совпадают")
            return [start]
        
        # Преобразование координат в индексы сетки
        resolution = self.map_data['resolution']
        origin_x = self.map_data['origin']['x']
        origin_y = self.map_data['origin']['y']
        
        start_grid = self._world_to_grid(start[0], start[1])
        goal_grid = self._world_to_grid(goal[0], goal[1])
        
        # A* алгоритм
        # Открытый список: приоритетная очередь (f_score, counter, node)
        open_set = []
        counter = 0
        heapq.heappush(open_set, (0, counter, start_grid))
        counter += 1
        
        # Закрытый список
        closed_set = set()
        
        # Словари для хранения пути и стоимостей
        came_from = {}
        g_score = defaultdict(lambda: float('inf'))
        g_score[start_grid] = 0
        
        f_score = defaultdict(lambda: float('inf'))
        f_score[start_grid] = self._heuristic(start_grid, goal_grid)
        
        iterations = 0
        
        while open_set and iterations < MAX_PLANNING_ITERATIONS:
            iterations += 1
            
            # Извлечение узла с наименьшим f_score
            current_f, _, current = heapq.heappop(open_set)
            
            # Проверка достижения цели
            if current == goal_grid:
                self.logger.info(f"Путь найден за {iterations} итераций")
                # Восстановление пути
                path = self._reconstruct_path(came_from, current)
                # Преобразование обратно в мировые координаты
                world_path = [self._grid_to_world(node[0], node[1]) for node in path]
                # Упрощение пути (удаление лишних точек)
                simplified_path = self._simplify_path(world_path)
                
                # Сброс счетчика ошибок при успешном планировании
                self.path_planning_failures = 0
                
                return simplified_path
            
            closed_set.add(current)
            
            # Проверка соседей
            for neighbor in self._get_neighbors(current):
                if neighbor in closed_set:
                    continue
                
                # Проверка валидности соседа (не препятствие, с учетом зазора)
                neighbor_world = self._grid_to_world(neighbor[0], neighbor[1])
                if not self._is_valid_position(neighbor_world[0], neighbor_world[1], OBSTACLE_CLEARANCE):
                    continue
                
                # Вычисление tentative g_score
                tentative_g = g_score[current] + self._distance(
                    self._grid_to_world(current[0], current[1]),
                    neighbor_world
                )
                
                if tentative_g < g_score[neighbor]:
                    # Этот путь лучше
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._heuristic(neighbor, goal_grid)
                    
                    # Добавление в открытый список, если еще не там
                    if neighbor not in [item[2] for item in open_set]:
                        heapq.heappush(open_set, (f_score[neighbor], counter, neighbor))
                        counter += 1
        
        # Путь не найден
        self.path_planning_failures += 1
        self.logger.warning(f"Путь не найден после {iterations} итераций (ошибка {self.path_planning_failures})")
        
        # Если это не первая ошибка, выбрасываем исключение
        if self.path_planning_failures >= MAX_RECOVERY_ATTEMPTS:
            raise PathPlanningFailureError(
                f"Не удалось спланировать путь после {MAX_RECOVERY_ATTEMPTS} попыток"
            )
        
        return []
    
    def _find_nearest_valid_position(self, x: float, y: float, max_search_radius: float = 1.0) -> Optional[Tuple[float, float]]:
        """
        Поиск ближайшей валидной позиции к заданной точке
        
        Args:
            x: Координата X
            y: Координата Y
            max_search_radius: Максимальный радиус поиска в метрах
            
        Returns:
            Ближайшая валидная позиция (x, y) или None если не найдена
        """
        from config import MAP_RESOLUTION
        
        # Поиск по спирали от центра
        step = MAP_RESOLUTION
        for radius in np.arange(step, max_search_radius, step):
            # Проверка точек на окружности
            num_points = int(2 * np.pi * radius / step)
            for i in range(num_points):
                angle = 2 * np.pi * i / num_points
                test_x = x + radius * np.cos(angle)
                test_y = y + radius * np.sin(angle)
                
                if self._is_valid_position(test_x, test_y):
                    self.logger.info(f"Найдена валидная позиция ({test_x:.2f}, {test_y:.2f}) на расстоянии {radius:.2f}м")
                    return (test_x, test_y)
        
        return None
    
    def _world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """
        Преобразование мировых координат в индексы сетки
        
        Args:
            x: Координата X в метрах
            y: Координата Y в метрах
            
        Returns:
            Кортеж (grid_x, grid_y)
        """
        resolution = self.map_data['resolution']
        origin_x = self.map_data['origin']['x']
        origin_y = self.map_data['origin']['y']
        
        grid_x = int((x - origin_x) / resolution)
        grid_y = int((y - origin_y) / resolution)
        
        return (grid_x, grid_y)
    
    def _grid_to_world(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """
        Преобразование индексов сетки в мировые координаты
        
        Args:
            grid_x: Индекс X в сетке
            grid_y: Индекс Y в сетке
            
        Returns:
            Кортеж (x, y) в метрах
        """
        resolution = self.map_data['resolution']
        origin_x = self.map_data['origin']['x']
        origin_y = self.map_data['origin']['y']
        
        x = origin_x + (grid_x + 0.5) * resolution
        y = origin_y + (grid_y + 0.5) * resolution
        
        return (x, y)
    
    def _is_valid_position(self, x: float, y: float, clearance: float = 0.0) -> bool:
        """
        Проверка валидности позиции (не в препятствии, с учетом зазора)
        
        Args:
            x: Координата X в метрах
            y: Координата Y в метрах
            clearance: Минимальный зазор от препятствий в метрах
            
        Returns:
            True если позиция валидна, False иначе
        """
        resolution = self.map_data['resolution']
        clearance_cells = int(clearance / resolution)
        
        grid_x, grid_y = self._world_to_grid(x, y)
        
        # Проверка границ
        if (grid_x < 0 or grid_x >= self.occupancy_grid.shape[1] or
            grid_y < 0 or grid_y >= self.occupancy_grid.shape[0]):
            return False
        
        # Проверка препятствия с учетом зазора
        for dy in range(-clearance_cells, clearance_cells + 1):
            for dx in range(-clearance_cells, clearance_cells + 1):
                check_x = grid_x + dx
                check_y = grid_y + dy
                
                if (check_x >= 0 and check_x < self.occupancy_grid.shape[1] and
                    check_y >= 0 and check_y < self.occupancy_grid.shape[0]):
                    if self.occupancy_grid[check_y, check_x] == 1:
                        return False
        
        return True
    
    def _distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """
        Вычисление евклидова расстояния между двумя точками
        
        Args:
            pos1: Первая точка (x, y)
            pos2: Вторая точка (x, y)
            
        Returns:
            Расстояние в метрах
        """
        return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def _heuristic(self, node1: Tuple[int, int], node2: Tuple[int, int]) -> float:
        """
        Эвристическая функция для A* (евклидово расстояние)
        
        Args:
            node1: Первый узел (grid_x, grid_y)
            node2: Второй узел (grid_x, grid_y)
            
        Returns:
            Эвристическая оценка расстояния
        """
        pos1 = self._grid_to_world(node1[0], node1[1])
        pos2 = self._grid_to_world(node2[0], node2[1])
        return self._distance(pos1, pos2)
    
    def _get_neighbors(self, node: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Получение соседних узлов (8-связность)
        
        Args:
            node: Узел (grid_x, grid_y)
            
        Returns:
            Список соседних узлов
        """
        x, y = node
        neighbors = []
        
        # 8 направлений: вверх, вниз, влево, вправо и диагонали
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                
                nx, ny = x + dx, y + dy
                
                # Проверка границ
                if (nx >= 0 and nx < self.occupancy_grid.shape[1] and
                    ny >= 0 and ny < self.occupancy_grid.shape[0]):
                    neighbors.append((nx, ny))
        
        return neighbors
    
    def _reconstruct_path(self, came_from: dict, current: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Восстановление пути от начала до текущего узла
        
        Args:
            came_from: Словарь предшественников
            current: Текущий узел
            
        Returns:
            Список узлов пути
        """
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
    
    def _simplify_path(self, path: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Упрощение пути путем удаления промежуточных точек на прямых линиях
        
        Args:
            path: Исходный путь
            
        Returns:
            Упрощенный путь
        """
        if len(path) <= 2:
            return path
        
        simplified = [path[0]]
        
        for i in range(1, len(path) - 1):
            # Проверка, можно ли пропустить эту точку
            # (есть ли прямая видимость от предыдущей ключевой точки до следующей)
            if not self._has_line_of_sight(simplified[-1], path[i + 1]):
                simplified.append(path[i])
        
        simplified.append(path[-1])
        
        self.logger.debug(f"Путь упрощен с {len(path)} до {len(simplified)} точек")
        return simplified
    
    def _has_line_of_sight(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> bool:
        """
        Проверка прямой видимости между двумя точками
        
        Args:
            pos1: Первая точка (x, y)
            pos2: Вторая точка (x, y)
            
        Returns:
            True если есть прямая видимость, False иначе
        """
        from config import OBSTACLE_CLEARANCE
        
        # Количество шагов для проверки
        distance = self._distance(pos1, pos2)
        resolution = self.map_data['resolution']
        num_steps = int(distance / resolution) + 1
        
        for i in range(num_steps + 1):
            t = i / num_steps if num_steps > 0 else 0
            x = pos1[0] + t * (pos2[0] - pos1[0])
            y = pos1[1] + t * (pos2[1] - pos1[1])
            
            if not self._is_valid_position(x, y, OBSTACLE_CLEARANCE):
                return False
        
        return True

    def update_dynamic_obstacles(self) -> None:
        """
        Обновление динамических препятствий на основе данных LiDAR
        Интегрирует обнаруженные препятствия в сетку занятости
        """
        from config import OBSTACLE_MIN_DISTANCE
        
        try:
            # Получение препятствий от LiDAR
            obstacles = self.lidar.get_obstacles(OBSTACLE_MIN_DISTANCE)
            
            if not obstacles:
                return
            
            # Создание временной копии статической карты
            # (динамические препятствия не сохраняются между обновлениями)
            self.dynamic_occupancy_grid = self.occupancy_grid.copy()
            
            # Добавление динамических препятствий
            for obstacle_x, obstacle_y in obstacles:
                # Преобразование относительных координат в глобальные
                global_x = self.current_position.x + obstacle_x
                global_y = self.current_position.y + obstacle_y
                
                # Преобразование в индексы сетки
                grid_x, grid_y = self._world_to_grid(global_x, global_y)
                
                # Добавление препятствия в сетку с расширением (для безопасности)
                self._add_obstacle_to_grid(grid_x, grid_y)
            
            self.logger.debug(f"Обновлено {len(obstacles)} динамических препятствий")
            
        except Exception as e:
            self.logger.error(f"Ошибка обновления динамических препятствий: {e}")
    
    def _add_obstacle_to_grid(self, grid_x: int, grid_y: int, radius: int = 2) -> None:
        """
        Добавление препятствия в сетку занятости с расширением
        
        Args:
            grid_x: Координата X в сетке
            grid_y: Координата Y в сетке
            radius: Радиус расширения препятствия (в ячейках сетки)
        """
        if not hasattr(self, 'dynamic_occupancy_grid'):
            self.dynamic_occupancy_grid = self.occupancy_grid.copy()
        
        # Расширение препятствия для безопасности
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                check_x = grid_x + dx
                check_y = grid_y + dy
                
                # Проверка границ
                if (check_x >= 0 and check_x < self.dynamic_occupancy_grid.shape[1] and
                    check_y >= 0 and check_y < self.dynamic_occupancy_grid.shape[0]):
                    # Проверка, что точка в пределах радиуса
                    if dx*dx + dy*dy <= radius*radius:
                        self.dynamic_occupancy_grid[check_y, check_x] = 1
    
    def plan_path_with_dynamic_obstacles(self, start: Tuple[float, float], 
                                        goal: Tuple[float, float]) -> List[Tuple[float, float]]:
        """
        Планирование пути с учетом динамических препятствий
        Обновляет динамические препятствия перед планированием
        
        Args:
            start: Начальная позиция (x, y) в метрах
            goal: Целевая позиция (x, y) в метрах
            
        Returns:
            Список точек пути [(x1, y1), (x2, y2), ...] или пустой список если путь не найден
        """
        # Обновление динамических препятствий
        self.update_dynamic_obstacles()
        
        # Временно заменяем статическую сетку на динамическую
        original_grid = self.occupancy_grid
        if hasattr(self, 'dynamic_occupancy_grid'):
            self.occupancy_grid = self.dynamic_occupancy_grid
        
        try:
            # Планирование пути с учетом динамических препятствий
            path = self.plan_path(start, goal)
            return path
        finally:
            # Восстановление статической сетки
            self.occupancy_grid = original_grid
    
    def check_path_collision(self, path: List[Tuple[float, float]]) -> bool:
        """
        Проверка пути на столкновение с динамическими препятствиями
        
        Args:
            path: Путь для проверки
            
        Returns:
            True если путь свободен, False если есть столкновение
        """
        from config import OBSTACLE_CLEARANCE
        
        # Обновление динамических препятствий
        self.update_dynamic_obstacles()
        
        if not hasattr(self, 'dynamic_occupancy_grid'):
            return True
        
        # Проверка каждой точки пути
        for x, y in path:
            grid_x, grid_y = self._world_to_grid(x, y)
            
            # Проверка с учетом зазора
            clearance_cells = int(OBSTACLE_CLEARANCE / self.map_data['resolution'])
            
            for dy in range(-clearance_cells, clearance_cells + 1):
                for dx in range(-clearance_cells, clearance_cells + 1):
                    check_x = grid_x + dx
                    check_y = grid_y + dy
                    
                    if (check_x >= 0 and check_x < self.dynamic_occupancy_grid.shape[1] and
                        check_y >= 0 and check_y < self.dynamic_occupancy_grid.shape[0]):
                        if self.dynamic_occupancy_grid[check_y, check_x] == 1:
                            return False
        
        return True
    
    def replan_if_needed(self, current_path: List[Tuple[float, float]], 
                        goal: Tuple[float, float]) -> Tuple[bool, List[Tuple[float, float]]]:
        """
        Проверка необходимости перепланирования и выполнение при необходимости
        
        Args:
            current_path: Текущий путь
            goal: Целевая позиция
            
        Returns:
            Кортеж (нужно_перепланирование, новый_путь)
        """
        # Проверка текущего пути на столкновения
        if not self.check_path_collision(current_path):
            self.logger.warning("Обнаружено препятствие на пути, перепланирование...")
            
            # Перепланирование с текущей позиции
            current_pos = (self.current_position.x, self.current_position.y)
            new_path = self.plan_path_with_dynamic_obstacles(current_pos, goal)
            
            if new_path:
                self.logger.info("Путь успешно перепланирован")
                return (True, new_path)
            else:
                self.logger.error("Не удалось перепланировать путь")
                return (True, [])
        
        return (False, current_path)
    
    def navigate_to(self, target_x: float, target_y: float) -> bool:
        """
        Навигация к целевой точке с использованием планирования пути и PID контроллера
        Включает обработку ошибок с повторными попытками и экспоненциальной задержкой
        
        Args:
            target_x: Целевая координата X в метрах
            target_y: Целевая координата Y в метрах
            
        Returns:
            True если цель достигнута, False если произошла ошибка
            
        Raises:
            LocalizationFailureError: Если не удалось восстановить локализацию
            PathPlanningFailureError: Если не удалось спланировать путь
            GoalUnreachableError: Если цель недостижима (застревание)
            ObstacleCollisionError: Если обнаружено критическое препятствие
            NavigationError: Для других критических ошибок навигации
        """
        from config import MAX_RECOVERY_ATTEMPTS, RECOVERY_RETRY_DELAY
        
        # Попытки навигации с экспоненциальной задержкой
        for attempt in range(MAX_RECOVERY_ATTEMPTS):
            try:
                return self._navigate_to_internal(target_x, target_y)
            except (LocalizationFailureError, PathPlanningFailureError, GoalUnreachableError, 
                    ObstacleCollisionError) as e:
                self.logger.error(f"Ошибка навигации (попытка {attempt + 1}/{MAX_RECOVERY_ATTEMPTS}): {e}")
                
                if attempt < MAX_RECOVERY_ATTEMPTS - 1:
                    # Экспоненциальная задержка перед повторной попыткой
                    delay = RECOVERY_RETRY_DELAY * (2 ** attempt)
                    self.logger.info(f"Повторная попытка через {delay:.1f} секунд...")
                    time.sleep(delay)
                    
                    # Сброс счетчиков ошибок для новой попытки
                    self.path_planning_failures = 0
                    self.stuck_detections = 0
                else:
                    # Последняя попытка не удалась, выбрасываем исключение
                    self.logger.error(f"Навигация не удалась после {MAX_RECOVERY_ATTEMPTS} попыток")
                    raise
            except Exception as e:
                # Неожиданная ошибка
                self.logger.error(f"Неожиданная ошибка навигации: {e}")
                self.stop()
                raise NavigationError(f"Критическая ошибка навигации: {e}")
        
        return False
    
    def _navigate_to_internal(self, target_x: float, target_y: float) -> bool:
        """
        Внутренняя реализация навигации (вызывается из navigate_to с обработкой ошибок)
        
        Args:
            target_x: Целевая координата X в метрах
            target_y: Целевая координата Y в метрах
            
        Returns:
            True если цель достигнута, False если произошла ошибка
        """
        from config import (POSITION_TOLERANCE, MAX_SPEED, MIN_SPEED, 
                           PID_LINEAR_KP, PID_LINEAR_KI, PID_LINEAR_KD,
                           PID_ANGULAR_KP, PID_ANGULAR_KI, PID_ANGULAR_KD,
                           MAX_STUCK_TIME, STUCK_THRESHOLD, NAVIGATION_UPDATE_RATE)
        import time
        
        self.logger.info(f"Начало навигации к цели ({target_x:.2f}, {target_y:.2f})")
        
        # Сброс флага остановки
        self.is_stopped = False
        
        # Получение текущей позиции
        current_pos = (self.current_position.x, self.current_position.y)
        target_pos = (target_x, target_y)
        
        # Проверка, не находимся ли мы уже в цели
        distance_to_goal = self._distance(current_pos, target_pos)
        if distance_to_goal < POSITION_TOLERANCE:
            self.logger.info("Уже в целевой позиции")
            self.stop()
            return True
        
        # Планирование пути с учетом динамических препятствий
        path = self.plan_path_with_dynamic_obstacles(current_pos, target_pos)
        
        if not path or len(path) == 0:
            self.logger.error("Не удалось спланировать путь к цели")
            self.stop()
            return False
        
        self.logger.info(f"Путь спланирован, {len(path)} точек")
        
        # Инициализация PID контроллеров
        linear_pid = PIDController(PID_LINEAR_KP, PID_LINEAR_KI, PID_LINEAR_KD)
        angular_pid = PIDController(PID_ANGULAR_KP, PID_ANGULAR_KI, PID_ANGULAR_KD)
        
        # Индекс текущей целевой точки пути
        current_waypoint_idx = 0
        
        # Переменные для обнаружения застревания
        last_position = current_pos
        stuck_timer = 0.0
        last_check_time = time.time()
        
        # Переменные для перепланирования
        replan_counter = 0
        max_replans = 5
        
        # Главный цикл навигации
        update_period = 1.0 / NAVIGATION_UPDATE_RATE
        
        while not self.is_stopped:
            loop_start_time = time.time()
            
            # Обновление локализации
            self.update_localization()
            current_pos = (self.current_position.x, self.current_position.y)
            current_theta = self.current_position.theta
            
            # Проверка достижения конечной цели
            distance_to_goal = self._distance(current_pos, target_pos)
            if distance_to_goal < POSITION_TOLERANCE:
                self.logger.info(f"Цель достигнута! Расстояние: {distance_to_goal:.3f}м")
                self.stop()
                return True
            
            # Получение текущей целевой точки пути
            if current_waypoint_idx >= len(path):
                # Достигли конца пути, но не достигли цели - возможно нужно перепланирование
                self.logger.warning("Достигнут конец пути, но цель не достигнута")
                
                if replan_counter < max_replans:
                    self.logger.info("Попытка перепланирования...")
                    path = self.plan_path_with_dynamic_obstacles(current_pos, target_pos)
                    
                    if path and len(path) > 0:
                        current_waypoint_idx = 0
                        replan_counter += 1
                        continue
                    else:
                        self.logger.error("Перепланирование не удалось")
                        self.stop()
                        return False
                else:
                    self.logger.error("Превышено максимальное количество перепланирований")
                    self.stop()
                    return False
            
            waypoint = path[current_waypoint_idx]
            
            # Проверка достижения текущей точки пути
            distance_to_waypoint = self._distance(current_pos, waypoint)
            if distance_to_waypoint < POSITION_TOLERANCE:
                self.logger.debug(f"Достигнута точка пути {current_waypoint_idx + 1}/{len(path)}")
                current_waypoint_idx += 1
                continue
            
            # Вычисление ошибок для PID контроллеров
            # Линейная ошибка - расстояние до точки пути
            linear_error = distance_to_waypoint
            
            # Угловая ошибка - разница между текущим углом и углом к точке пути
            desired_angle = np.arctan2(waypoint[1] - current_pos[1], 
                                      waypoint[0] - current_pos[0])
            angular_error = self._normalize_angle(desired_angle - current_theta)
            
            # Вычисление управляющих сигналов
            linear_control = linear_pid.update(linear_error, update_period)
            angular_control = angular_pid.update(angular_error, update_period)
            
            # Преобразование управляющих сигналов в скорости моторов
            # Линейная скорость влияет на оба мотора одинаково
            # Угловая скорость создает разницу между моторами
            
            # Ограничение линейной скорости
            linear_speed = np.clip(linear_control * MAX_SPEED, MIN_SPEED, MAX_SPEED)
            
            # Если угловая ошибка большая, уменьшаем линейную скорость
            if abs(angular_error) > np.pi / 4:  # 45 градусов
                linear_speed *= 0.5
            
            # Вычисление скоростей левого и правого моторов
            left_speed = linear_speed - angular_control * MAX_SPEED * 0.5
            right_speed = linear_speed + angular_control * MAX_SPEED * 0.5
            
            # Ограничение скоростей
            left_speed = np.clip(left_speed, -MAX_SPEED, MAX_SPEED)
            right_speed = np.clip(right_speed, -MAX_SPEED, MAX_SPEED)
            
            # Определение направлений моторов
            left_dir = 1 if left_speed >= 0 else 0
            right_dir = 1 if right_speed >= 0 else 0
            
            # Преобразование в абсолютные значения
            left_speed_abs = int(abs(left_speed))
            right_speed_abs = int(abs(right_speed))
            
            # Проверка IR сенсора перед отправкой команды движения
            try:
                self._check_ir_sensor_emergency_stop()
            except ObstacleCollisionError as e:
                self.logger.error(f"Экстренная остановка из-за препятствия: {e}")
                # Попытка отступить назад
                try:
                    self.logger.info("Попытка отступить назад...")
                    self.serial.send_motor_command(50, 50, 0, 0)  # Назад на малой скорости
                    time.sleep(1.0)  # Отступаем 1 секунду
                    self.stop()
                    
                    # Перепланирование пути
                    if replan_counter < max_replans:
                        self.logger.info("Перепланирование после столкновения...")
                        current_pos = (self.current_position.x, self.current_position.y)
                        path = self.plan_path_with_dynamic_obstacles(current_pos, target_pos)
                        
                        if path and len(path) > 0:
                            current_waypoint_idx = 0
                            replan_counter += 1
                            continue
                        else:
                            raise GoalUnreachableError("Не удалось перепланировать путь после столкновения")
                    else:
                        raise GoalUnreachableError("Превышен лимит перепланирований после столкновения")
                except Exception as recovery_error:
                    self.logger.error(f"Ошибка восстановления после столкновения: {recovery_error}")
                    raise
            
            # Отправка команды моторам с повторными попытками
            from config import SERIAL_MAX_RETRIES, RECOVERY_RETRY_DELAY
            
            motor_command_sent = False
            for attempt in range(SERIAL_MAX_RETRIES):
                try:
                    self.serial.send_motor_command(left_speed_abs, right_speed_abs, 
                                                  left_dir, right_dir)
                    motor_command_sent = True
                    break
                except Exception as e:
                    self.logger.warning(f"Ошибка отправки команды моторам (попытка {attempt + 1}/{SERIAL_MAX_RETRIES}): {e}")
                    if attempt < SERIAL_MAX_RETRIES - 1:
                        time.sleep(RECOVERY_RETRY_DELAY * (2 ** attempt))  # Экспоненциальная задержка
                    else:
                        self.logger.error("Не удалось отправить команду моторам после всех попыток")
                        self.stop()
                        raise NavigationError(f"Ошибка связи с моторами: {e}")
            
            if not motor_command_sent:
                self.stop()
                raise NavigationError("Не удалось отправить команду моторам")
            
            # Проверка застревания
            current_time = time.time()
            time_delta = current_time - last_check_time
            
            if time_delta >= 1.0:  # Проверка каждую секунду
                distance_moved = self._distance(current_pos, last_position)
                
                if distance_moved < STUCK_THRESHOLD:
                    stuck_timer += time_delta
                    self.stuck_detections += 1
                    self.logger.warning(f"Возможно застревание: {stuck_timer:.1f}с (обнаружений: {self.stuck_detections})")
                    
                    if stuck_timer >= MAX_STUCK_TIME:
                        self.logger.error("Робот застрял, навигация прервана")
                        self.stop()
                        raise GoalUnreachableError(
                            f"Робот застрял на позиции ({current_pos[0]:.2f}, {current_pos[1]:.2f}) "
                            f"на {stuck_timer:.1f} секунд"
                        )
                else:
                    stuck_timer = 0.0
                    if self.stuck_detections > 0:
                        self.logger.info("Движение восстановлено")
                        self.stuck_detections = 0
                
                last_position = current_pos
                last_check_time = current_time
            
            # Проверка необходимости перепланирования из-за препятствий
            if current_waypoint_idx < len(path):
                # Проверяем оставшуюся часть пути
                remaining_path = path[current_waypoint_idx:]
                
                if not self.check_path_collision(remaining_path):
                    self.logger.warning("Обнаружено препятствие на пути")
                    
                    if replan_counter < max_replans:
                        self.logger.info("Перепланирование из-за препятствия...")
                        new_path = self.plan_path_with_dynamic_obstacles(current_pos, target_pos)
                        
                        if new_path and len(new_path) > 0:
                            path = new_path
                            current_waypoint_idx = 0
                            replan_counter += 1
                            self.logger.info("Путь успешно перепланирован")
                        else:
                            self.logger.warning("Перепланирование не удалось, продолжаем по старому пути")
                    else:
                        self.logger.warning("Превышен лимит перепланирований, продолжаем движение")
            
            # Ожидание до следующего обновления
            elapsed = time.time() - loop_start_time
            if elapsed < update_period:
                time.sleep(update_period - elapsed)
        
        # Если цикл прерван (is_stopped = True)
        self.logger.warning("Навигация прервана")
        self.stop()
        return False


class PIDController:
    """
    Простой PID контроллер для управления движением
    """
    
    def __init__(self, kp: float, ki: float, kd: float):
        """
        Инициализация PID контроллера
        
        Args:
            kp: Пропорциональный коэффициент
            ki: Интегральный коэффициент
            kd: Дифференциальный коэффициент
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        self.integral = 0.0
        self.previous_error = 0.0
    
    def update(self, error: float, dt: float) -> float:
        """
        Обновление PID контроллера
        
        Args:
            error: Текущая ошибка
            dt: Временной интервал с предыдущего обновления
            
        Returns:
            Управляющий сигнал
        """
        # Пропорциональная составляющая
        p_term = self.kp * error
        
        # Интегральная составляющая
        self.integral += error * dt
        i_term = self.ki * self.integral
        
        # Дифференциальная составляющая
        if dt > 0:
            derivative = (error - self.previous_error) / dt
        else:
            derivative = 0.0
        d_term = self.kd * derivative
        
        # Сохранение ошибки для следующей итерации
        self.previous_error = error
        
        # Управляющий сигнал
        output = p_term + i_term + d_term
        
        return output
    
    def reset(self):
        """Сброс состояния контроллера"""
        self.integral = 0.0
        self.previous_error = 0.0

        def navigate_to(self, target_x: float, target_y: float) -> bool:
            """
            Навигация к целевой точке с использованием планирования пути и PID контроллера

            Args:
                target_x: Целевая координата X в метрах
                target_y: Целевая координата Y в метрах

            Returns:
                True если цель достигнута, False если произошла ошибка
            """
            from config import (POSITION_TOLERANCE, MAX_SPEED, MIN_SPEED,
                               PID_LINEAR_KP, PID_LINEAR_KI, PID_LINEAR_KD,
                               PID_ANGULAR_KP, PID_ANGULAR_KI, PID_ANGULAR_KD,
                               MAX_STUCK_TIME, STUCK_THRESHOLD, NAVIGATION_UPDATE_RATE)
            import time

            self.logger.info(f"Начало навигации к цели ({target_x:.2f}, {target_y:.2f})")

            # Сброс флага остановки
            self.is_stopped = False

            # Получение текущей позиции
            current_pos = (self.current_position.x, self.current_position.y)
            target_pos = (target_x, target_y)

            # Проверка, не находимся ли мы уже в цели
            distance_to_goal = self._distance(current_pos, target_pos)
            if distance_to_goal < POSITION_TOLERANCE:
                self.logger.info("Уже в целевой позиции")
                self.stop()
                return True

            # Планирование пути с учетом динамических препятствий
            path = self.plan_path_with_dynamic_obstacles(current_pos, target_pos)

            if not path or len(path) == 0:
                self.logger.error("Не удалось спланировать путь к цели")
                self.stop()
                return False

            self.logger.info(f"Путь спланирован, {len(path)} точек")

            # Инициализация PID контроллеров
            linear_pid = PIDController(PID_LINEAR_KP, PID_LINEAR_KI, PID_LINEAR_KD)
            angular_pid = PIDController(PID_ANGULAR_KP, PID_ANGULAR_KI, PID_ANGULAR_KD)

            # Индекс текущей целевой точки пути
            current_waypoint_idx = 0

            # Переменные для обнаружения застревания
            last_position = current_pos
            stuck_timer = 0.0
            last_check_time = time.time()

            # Переменные для перепланирования
            replan_counter = 0
            max_replans = 5

            # Главный цикл навигации
            update_period = 1.0 / NAVIGATION_UPDATE_RATE

            while not self.is_stopped:
                loop_start_time = time.time()

                # Обновление локализации
                self.update_localization()
                current_pos = (self.current_position.x, self.current_position.y)
                current_theta = self.current_position.theta

                # Проверка достижения конечной цели
                distance_to_goal = self._distance(current_pos, target_pos)
                if distance_to_goal < POSITION_TOLERANCE:
                    self.logger.info(f"Цель достигнута! Расстояние: {distance_to_goal:.3f}м")
                    self.stop()
                    return True

                # Получение текущей целевой точки пути
                if current_waypoint_idx >= len(path):
                    # Достигли конца пути, но не достигли цели - возможно нужно перепланирование
                    self.logger.warning("Достигнут конец пути, но цель не достигнута")

                    if replan_counter < max_replans:
                        self.logger.info("Попытка перепланирования...")
                        path = self.plan_path_with_dynamic_obstacles(current_pos, target_pos)

                        if path and len(path) > 0:
                            current_waypoint_idx = 0
                            replan_counter += 1
                            continue
                        else:
                            self.logger.error("Перепланирование не удалось")
                            self.stop()
                            return False
                    else:
                        self.logger.error("Превышено максимальное количество перепланирований")
                        self.stop()
                        return False

                waypoint = path[current_waypoint_idx]

                # Проверка достижения текущей точки пути
                distance_to_waypoint = self._distance(current_pos, waypoint)
                if distance_to_waypoint < POSITION_TOLERANCE:
                    self.logger.debug(f"Достигнута точка пути {current_waypoint_idx + 1}/{len(path)}")
                    current_waypoint_idx += 1
                    continue

                # Вычисление ошибок для PID контроллеров
                # Линейная ошибка - расстояние до точки пути
                linear_error = distance_to_waypoint

                # Угловая ошибка - разница между текущим углом и углом к точке пути
                desired_angle = np.arctan2(waypoint[1] - current_pos[1],
                                          waypoint[0] - current_pos[0])
                angular_error = self._normalize_angle(desired_angle - current_theta)

                # Вычисление управляющих сигналов
                linear_control = linear_pid.update(linear_error, update_period)
                angular_control = angular_pid.update(angular_error, update_period)

                # Преобразование управляющих сигналов в скорости моторов
                # Линейная скорость влияет на оба мотора одинаково
                # Угловая скорость создает разницу между моторами

                # Ограничение линейной скорости
                linear_speed = np.clip(linear_control * MAX_SPEED, MIN_SPEED, MAX_SPEED)

                # Если угловая ошибка большая, уменьшаем линейную скорость
                if abs(angular_error) > np.pi / 4:  # 45 градусов
                    linear_speed *= 0.5

                # Вычисление скоростей левого и правого моторов
                left_speed = linear_speed - angular_control * MAX_SPEED * 0.5
                right_speed = linear_speed + angular_control * MAX_SPEED * 0.5

                # Ограничение скоростей
                left_speed = np.clip(left_speed, -MAX_SPEED, MAX_SPEED)
                right_speed = np.clip(right_speed, -MAX_SPEED, MAX_SPEED)

                # Определение направлений моторов
                left_dir = 1 if left_speed >= 0 else 0
                right_dir = 1 if right_speed >= 0 else 0

                # Преобразование в абсолютные значения
                left_speed_abs = int(abs(left_speed))
                right_speed_abs = int(abs(right_speed))

                # Отправка команды моторам
                try:
                    self.serial.send_motor_command(left_speed_abs, right_speed_abs,
                                                  left_dir, right_dir)
                except Exception as e:
                    self.logger.error(f"Ошибка отправки команды моторам: {e}")
                    self.stop()
                    return False

                # Проверка застревания
                current_time = time.time()
                time_delta = current_time - last_check_time

                if time_delta >= 1.0:  # Проверка каждую секунду
                    distance_moved = self._distance(current_pos, last_position)

                    if distance_moved < STUCK_THRESHOLD:
                        stuck_timer += time_delta
                        self.logger.warning(f"Возможно застревание: {stuck_timer:.1f}с")

                        if stuck_timer >= MAX_STUCK_TIME:
                            self.logger.error("Робот застрял, навигация прервана")
                            self.stop()
                            return False
                    else:
                        stuck_timer = 0.0

                    last_position = current_pos
                    last_check_time = current_time

                # Проверка необходимости перепланирования из-за препятствий
                if current_waypoint_idx < len(path):
                    # Проверяем оставшуюся часть пути
                    remaining_path = path[current_waypoint_idx:]

                    if not self.check_path_collision(remaining_path):
                        self.logger.warning("Обнаружено препятствие на пути")

                        if replan_counter < max_replans:
                            self.logger.info("Перепланирование из-за препятствия...")
                            new_path = self.plan_path_with_dynamic_obstacles(current_pos, target_pos)

                            if new_path and len(new_path) > 0:
                                path = new_path
                                current_waypoint_idx = 0
                                replan_counter += 1
                                self.logger.info("Путь успешно перепланирован")
                            else:
                                self.logger.warning("Перепланирование не удалось, продолжаем по старому пути")
                        else:
                            self.logger.warning("Превышен лимит перепланирований, продолжаем движение")

                # Ожидание до следующего обновления
                elapsed = time.time() - loop_start_time
                if elapsed < update_period:
                    time.sleep(update_period - elapsed)

            # Если цикл прерван (is_stopped = True)
            self.logger.warning("Навигация прервана")
            self.stop()
            return False


    class PIDController:
        """
        Простой PID контроллер для управления движением
        """

        def __init__(self, kp: float, ki: float, kd: float):
            """
            Инициализация PID контроллера

            Args:
                kp: Пропорциональный коэффициент
                ki: Интегральный коэффициент
                kd: Дифференциальный коэффициент
            """
            self.kp = kp
            self.ki = ki
            self.kd = kd

            self.integral = 0.0
            self.previous_error = 0.0

        def update(self, error: float, dt: float) -> float:
            """
            Обновление PID контроллера

            Args:
                error: Текущая ошибка
                dt: Временной интервал с предыдущего обновления

            Returns:
                Управляющий сигнал
            """
            # Пропорциональная составляющая
            p_term = self.kp * error

            # Интегральная составляющая
            self.integral += error * dt
            i_term = self.ki * self.integral

            # Дифференциальная составляющая
            if dt > 0:
                derivative = (error - self.previous_error) / dt
            else:
                derivative = 0.0
            d_term = self.kd * derivative

            # Сохранение ошибки для следующей итерации
            self.previous_error = error

            # Управляющий сигнал
            output = p_term + i_term + d_term

            return output

        def reset(self):
            """Сброс состояния контроллера"""
            self.integral = 0.0
            self.previous_error = 0.0

