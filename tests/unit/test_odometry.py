# -*- coding: utf-8 -*-
"""
Модульные тесты для системы одометрии
"""

import pytest
import math
from odometry import OdometrySystem
import config


class TestOdometrySystem:
    """Тесты для класса OdometrySystem"""
    
    def test_initialization(self):
        """Тест инициализации системы одометрии"""
        odom = OdometrySystem(
            wheel_base=config.WHEEL_BASE,
            wheel_radius=config.WHEEL_RADIUS
        )
        
        assert odom.wheel_base == config.WHEEL_BASE
        assert odom.wheel_radius == config.WHEEL_RADIUS
        assert odom.ticks_per_rev == config.ENCODER_TICKS_PER_REVOLUTION
        assert odom.x == 0.0
        assert odom.y == 0.0
        assert odom.theta == 0.0
        assert odom.last_left_ticks == 0
        assert odom.last_right_ticks == 0
    
    def test_get_pose_initial(self):
        """Тест получения начальной позы"""
        odom = OdometrySystem(
            wheel_base=config.WHEEL_BASE,
            wheel_radius=config.WHEEL_RADIUS
        )
        
        x, y, theta = odom.get_pose()
        assert x == 0.0
        assert y == 0.0
        assert theta == 0.0
    
    def test_reset_to_origin(self):
        """Тест сброса одометрии к началу координат"""
        odom = OdometrySystem(
            wheel_base=config.WHEEL_BASE,
            wheel_radius=config.WHEEL_RADIUS
        )
        
        # Изменить позицию
        odom.x = 5.0
        odom.y = 3.0
        odom.theta = 1.5
        
        # Сбросить к началу
        odom.reset()
        
        x, y, theta = odom.get_pose()
        assert x == 0.0
        assert y == 0.0
        assert theta == 0.0
    
    def test_reset_to_custom_position(self):
        """Тест сброса одометрии к заданной позиции"""
        odom = OdometrySystem(
            wheel_base=config.WHEEL_BASE,
            wheel_radius=config.WHEEL_RADIUS
        )
        
        # Сбросить к заданной позиции
        odom.reset(x=2.5, y=1.5, theta=math.pi / 4)
        
        x, y, theta = odom.get_pose()
        assert x == 2.5
        assert y == 1.5
        assert abs(theta - math.pi / 4) < 1e-6
    
    def test_zero_movement(self):
        """Тест нулевого движения (нет тиков)"""
        odom = OdometrySystem(
            wheel_base=config.WHEEL_BASE,
            wheel_radius=config.WHEEL_RADIUS
        )
        
        # Обновить с нулевыми тиками
        odom.update(left_ticks=0, right_ticks=0, dt=0.1)
        
        x, y, theta = odom.get_pose()
        assert x == 0.0
        assert y == 0.0
        assert theta == 0.0
    
    def test_straight_line_movement(self):
        """Тест прямолинейного движения (равные тики)"""
        odom = OdometrySystem(
            wheel_base=config.WHEEL_BASE,
            wheel_radius=config.WHEEL_RADIUS
        )
        
        # Симулировать движение вперед: 100 тиков на каждое колесо
        odom.update(left_ticks=100, right_ticks=100, dt=0.1)
        
        x, y, theta = odom.get_pose()
        
        # Робот должен двигаться вперед по оси X (theta=0)
        # Расстояние = (100 тиков / 360 тиков_на_оборот) * (2 * pi * 0.05м)
        expected_distance = (100.0 / 360.0) * (2.0 * math.pi * 0.05)
        
        assert abs(x - expected_distance) < 1e-6
        assert abs(y) < 1e-6
        assert abs(theta) < 1e-6
    
    def test_pure_rotation_left(self):
        """Тест чистого поворота влево (противоположные направления колес)"""
        odom = OdometrySystem(
            wheel_base=config.WHEEL_BASE,
            wheel_radius=config.WHEEL_RADIUS
        )
        
        # Левое колесо назад, правое вперед (поворот влево на месте)
        odom.update(left_ticks=-50, right_ticks=50, dt=0.1)
        
        x, y, theta = odom.get_pose()
        
        # При повороте на месте, центр робота не должен сильно сместиться
        # но theta должен измениться
        assert abs(x) < 0.1  # Небольшое смещение допустимо
        assert abs(y) < 0.1
        assert theta > 0  # Поворот против часовой стрелки (положительный)
    
    def test_pure_rotation_right(self):
        """Тест чистого поворота вправо"""
        odom = OdometrySystem(
            wheel_base=config.WHEEL_BASE,
            wheel_radius=config.WHEEL_RADIUS
        )
        
        # Левое колесо вперед, правое назад (поворот вправо на месте)
        odom.update(left_ticks=50, right_ticks=-50, dt=0.1)
        
        x, y, theta = odom.get_pose()
        
        # При повороте на месте, центр робота не должен сильно сместиться
        assert abs(x) < 0.1
        assert abs(y) < 0.1
        assert theta < 0  # Поворот по часовой стрелке (отрицательный)
    
    def test_curved_movement(self):
        """Тест движения по дуге (разные тики на колесах)"""
        odom = OdometrySystem(
            wheel_base=config.WHEEL_BASE,
            wheel_radius=config.WHEEL_RADIUS
        )
        
        # Правое колесо движется быстрее - поворот влево
        odom.update(left_ticks=80, right_ticks=120, dt=0.1)
        
        x, y, theta = odom.get_pose()
        
        # Робот должен двигаться вперед и поворачивать
        assert x > 0  # Движение вперед
        assert theta > 0  # Поворот влево (против часовой стрелки)
    
    def test_multiple_updates(self):
        """Тест множественных обновлений одометрии"""
        odom = OdometrySystem(
            wheel_base=config.WHEEL_BASE,
            wheel_radius=config.WHEEL_RADIUS
        )
        
        # Первое обновление: движение вперед
        odom.update(left_ticks=100, right_ticks=100, dt=0.1)
        x1, y1, theta1 = odom.get_pose()
        
        # Второе обновление: еще движение вперед
        odom.update(left_ticks=200, right_ticks=200, dt=0.1)
        x2, y2, theta2 = odom.get_pose()
        
        # Позиция должна увеличиться
        assert x2 > x1
        assert abs(y2 - y1) < 1e-6  # Y не должен измениться при прямом движении
        assert abs(theta2 - theta1) < 1e-6  # Угол не должен измениться
    
    def test_angle_normalization(self):
        """Тест нормализации угла в диапазон [-π, π]"""
        odom = OdometrySystem(
            wheel_base=config.WHEEL_BASE,
            wheel_radius=config.WHEEL_RADIUS
        )
        
        # Установить угол больше π
        odom.reset(x=0.0, y=0.0, theta=4.0 * math.pi)
        
        x, y, theta = odom.get_pose()
        
        # Угол должен быть нормализован
        assert theta >= -math.pi
        assert theta <= math.pi
    
    def test_backward_movement(self):
        """Тест движения назад (отрицательные тики)"""
        odom = OdometrySystem(
            wheel_base=config.WHEEL_BASE,
            wheel_radius=config.WHEEL_RADIUS
        )
        
        # Движение назад
        odom.update(left_ticks=-100, right_ticks=-100, dt=0.1)
        
        x, y, theta = odom.get_pose()
        
        # Робот должен двигаться назад (отрицательный X при theta=0)
        assert x < 0
        assert abs(y) < 1e-6
        assert abs(theta) < 1e-6
    
    def test_incremental_updates(self):
        """Тест инкрементальных обновлений (дельта тиков)"""
        odom = OdometrySystem(
            wheel_base=config.WHEEL_BASE,
            wheel_radius=config.WHEEL_RADIUS
        )
        
        # Первое обновление: 100 тиков
        odom.update(left_ticks=100, right_ticks=100, dt=0.1)
        x1, y1, theta1 = odom.get_pose()
        
        # Второе обновление: 150 тиков (дельта = 50)
        odom.update(left_ticks=150, right_ticks=150, dt=0.1)
        x2, y2, theta2 = odom.get_pose()
        
        # Вычислить ожидаемое изменение для 50 тиков
        distance_per_tick = (2.0 * math.pi * config.WHEEL_RADIUS) / config.ENCODER_TICKS_PER_REVOLUTION
        expected_delta = 50 * distance_per_tick
        
        # Проверить, что изменение соответствует дельте тиков
        actual_delta = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        assert abs(actual_delta - expected_delta) < 1e-6
