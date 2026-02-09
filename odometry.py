# -*- coding: utf-8 -*-
"""
Система одометрии для RelayBot
Отслеживает позицию робота через данные энкодеров колес
"""

import math
import time
import logging
from typing import Tuple
from navigation import Position
import config


class OdometryError(Exception):
    """Базовое исключение для ошибок одометрии"""
    pass


class EncoderFailureError(OdometryError):
    """Ошибка энкодера (нет обновлений данных)"""
    pass


class OdometrySystem:
    """
    Система одометрии для отслеживания позиции робота
    
    Использует дифференциальную кинематику для расчета позиции
    на основе тиков энкодеров левого и правого колес.
    
    Attributes:
        wheel_base: Расстояние между колесами в метрах
        wheel_radius: Радиус колеса в метрах
        ticks_per_rev: Количество тиков энкодера на один оборот колеса
        x: Текущая координата X в метрах
        y: Текущая координата Y в метрах
        theta: Текущая ориентация в радианах
        last_left_ticks: Последнее значение тиков левого колеса
        last_right_ticks: Последнее значение тиков правого колеса
    """
    
    def __init__(self, wheel_base: float, wheel_radius: float):
        """
        Инициализация системы одометрии
        
        Args:
            wheel_base: Расстояние между колесами в метрах
            wheel_radius: Радиус колеса в метрах
        """
        self.wheel_base = wheel_base
        self.wheel_radius = wheel_radius
        self.ticks_per_rev = config.ENCODER_TICKS_PER_REVOLUTION
        self.logger = logging.getLogger(__name__)
        
        # Текущая поза робота
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        
        # Последние значения энкодеров для расчета дельты
        self.last_left_ticks = 0
        self.last_right_ticks = 0
        
        # Отслеживание ошибок энкодера
        self.last_update_time = time.time()
        self.encoder_update_count = 0
        self.encoder_failure_detected = False
        self.consecutive_zero_updates = 0
    
    def update(self, left_ticks: int, right_ticks: int, dt: float) -> None:
        """
        Обновление одометрии на основе тиков энкодеров
        
        Использует дифференциальную кинематику для расчета изменения позиции:
        1. Вычисляет дельту тиков для каждого колеса
        2. Преобразует тики в пройденное расстояние
        3. Вычисляет линейное и угловое перемещение
        4. Обновляет позицию робота
        
        Args:
            left_ticks: Текущее значение тиков левого колеса
            right_ticks: Текущее значение тиков правого колеса
            dt: Временной интервал в секундах
            
        Raises:
            EncoderFailureError: Если обнаружена ошибка энкодера
        """
        current_time = time.time()
        
        # Проверка на слишком большой интервал между обновлениями
        time_since_last_update = current_time - self.last_update_time
        if time_since_last_update > 5.0 and self.encoder_update_count > 0:
            self.logger.warning(f"Большой интервал между обновлениями одометрии: {time_since_last_update:.1f}с")
        
        # Вычисляем изменение тиков с последнего обновления
        delta_left_ticks = left_ticks - self.last_left_ticks
        delta_right_ticks = right_ticks - self.last_right_ticks
        
        # Проверка на застывшие значения энкодера (возможная ошибка)
        if delta_left_ticks == 0 and delta_right_ticks == 0:
            self.consecutive_zero_updates += 1
            
            # Если робот должен двигаться, но энкодеры не обновляются - это ошибка
            # Однако мы не можем знать здесь, должен ли робот двигаться
            # Поэтому просто логируем предупреждение
            if self.consecutive_zero_updates > 50:  # 5 секунд при 10Hz
                self.logger.warning(f"Энкодеры не обновляются: {self.consecutive_zero_updates} итераций")
                # Не выбрасываем исключение, так как робот может быть остановлен
        else:
            # Сброс счетчика при получении обновлений
            if self.consecutive_zero_updates > 0:
                self.logger.debug("Обновления энкодера восстановлены")
                self.consecutive_zero_updates = 0
            
            if self.encoder_failure_detected:
                self.logger.info("Энкодеры восстановлены")
                self.encoder_failure_detected = False
        
        # Проверка на аномально большие изменения (возможная ошибка или переполнение)
        max_reasonable_delta = 1000  # Максимальное разумное изменение тиков за один цикл
        if abs(delta_left_ticks) > max_reasonable_delta or abs(delta_right_ticks) > max_reasonable_delta:
            self.logger.warning(
                f"Аномально большое изменение энкодера: left={delta_left_ticks}, right={delta_right_ticks}"
            )
            # Игнорируем это обновление, но сохраняем текущие значения
            self.last_left_ticks = left_ticks
            self.last_right_ticks = right_ticks
            self.last_update_time = current_time
            return
        
        # Сохраняем текущие значения для следующего обновления
        self.last_left_ticks = left_ticks
        self.last_right_ticks = right_ticks
        self.last_update_time = current_time
        self.encoder_update_count += 1
        
        # Преобразуем тики в пройденное расстояние для каждого колеса
        # Расстояние = (тики / тики_на_оборот) * окружность_колеса
        distance_per_tick = (2.0 * math.pi * self.wheel_radius) / self.ticks_per_rev
        left_distance = delta_left_ticks * distance_per_tick
        right_distance = delta_right_ticks * distance_per_tick
        
        # Вычисляем линейное перемещение центра робота
        # Для дифференциального привода: центр движется на среднее расстояние колес
        center_distance = (left_distance + right_distance) / 2.0
        
        # Вычисляем изменение ориентации (угловое перемещение)
        # Для дифференциального привода: delta_theta = (right - left) / wheel_base
        delta_theta = (right_distance - left_distance) / self.wheel_base
        
        # Обновляем позицию робота используя кинематическую модель
        # Если робот поворачивает (delta_theta != 0), используем дуговое движение
        # Если робот движется прямо (delta_theta ≈ 0), используем линейное движение
        
        if abs(delta_theta) < 1e-6:
            # Прямолинейное движение (без поворота)
            # Перемещение в направлении текущей ориентации
            delta_x = center_distance * math.cos(self.theta)
            delta_y = center_distance * math.sin(self.theta)
        else:
            # Дуговое движение (с поворотом)
            # Радиус поворота
            turn_radius = center_distance / delta_theta
            
            # Вычисляем изменение позиции через центр поворота
            delta_x = turn_radius * (math.sin(self.theta + delta_theta) - math.sin(self.theta))
            delta_y = turn_radius * (-math.cos(self.theta + delta_theta) + math.cos(self.theta))
        
        # Обновляем позицию
        self.x += delta_x
        self.y += delta_y
        self.theta += delta_theta
        
        # Нормализуем угол в диапазон [-π, π]
        self.theta = self._normalize_angle(self.theta)
        
        # Логирование обновления одометрии (каждые 10 обновлений для уменьшения объема логов)
        if self.encoder_update_count % 10 == 0:
            self.logger.debug(f"Одометрия: pos=({self.x:.3f}, {self.y:.3f}), theta={self.theta:.3f}, "
                            f"delta_ticks=({delta_left_ticks}, {delta_right_ticks})")
    
    def is_encoder_healthy(self) -> bool:
        """
        Проверка здоровья энкодеров
        
        Returns:
            True если энкодеры работают нормально, False если обнаружена проблема
        """
        # Проверка на слишком долгое отсутствие обновлений
        time_since_last_update = time.time() - self.last_update_time
        if time_since_last_update > 2.0 and self.encoder_update_count > 0:
            self.logger.warning("Энкодеры не обновлялись более 2 секунд")
            return False
        
        # Проверка на застывшие значения
        if self.consecutive_zero_updates > 100:  # 10 секунд при 10Hz
            self.logger.warning("Энкодеры застыли")
            return False
        
        return True
    
    def get_pose(self) -> Tuple[float, float, float]:
        """
        Получить текущую позу робота
        
        Returns:
            Кортеж (x, y, theta) где:
                x: координата X в метрах
                y: координата Y в метрах
                theta: ориентация в радианах
        """
        return (self.x, self.y, self.theta)
    
    def reset(self, x: float = 0.0, y: float = 0.0, theta: float = 0.0) -> None:
        """
        Сброс одометрии к заданной позиции
        
        Используется для инициализации позиции робота или коррекции
        на основе внешних данных локализации (например, от LiDAR).
        
        Args:
            x: Новая координата X в метрах (по умолчанию 0.0)
            y: Новая координата Y в метрах (по умолчанию 0.0)
            theta: Новая ориентация в радианах (по умолчанию 0.0)
        """
        self.x = x
        self.y = y
        self.theta = self._normalize_angle(theta)
        
        # Не сбрасываем last_left_ticks и last_right_ticks,
        # чтобы следующее обновление корректно вычислило дельту
    
    def _normalize_angle(self, angle: float) -> float:
        """
        Нормализация угла в диапазон [-π, π]
        
        Args:
            angle: Угол в радианах
            
        Returns:
            Нормализованный угол в диапазоне [-π, π]
        """
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle
