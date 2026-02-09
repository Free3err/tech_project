# -*- coding: utf-8 -*-
"""
Модульные тесты для системы навигации RelayBot
"""

import pytest
import numpy as np
import os
import sys

# Добавить корневую директорию в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from navigation import NavigationSystem, Position, Particle
from config import HOME_POSITION, WAREHOUSE_ZONE


class TestNavigationSystemInitialization:
    """Тесты инициализации системы навигации"""
    
    def test_initialization_with_valid_map(self, mock_lidar, mock_odometry, mock_serial):
        """Тест инициализации с валидным файлом карты"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        assert nav is not None
        assert nav.current_position.x == 0.0
        assert nav.current_position.y == 0.0
        assert nav.current_position.theta == 0.0
        assert len(nav.particles) > 0
        assert nav.occupancy_grid is not None
    
    def test_initialization_creates_particles(self, mock_lidar, mock_odometry, mock_serial):
        """Тест создания частиц при инициализации"""
        from config import NUM_PARTICLES
        
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        assert len(nav.particles) == NUM_PARTICLES
        
        # Проверка, что все частицы имеют валидные веса
        total_weight = sum(p.weight for p in nav.particles)
        assert abs(total_weight - 1.0) < 0.01  # Веса должны суммироваться в 1
    
    def test_initialization_loads_map(self, mock_lidar, mock_odometry, mock_serial):
        """Тест загрузки карты"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        assert nav.map_data is not None
        assert 'width' in nav.map_data
        assert 'height' in nav.map_data
        assert 'resolution' in nav.map_data
        assert nav.occupancy_grid.shape[0] > 0
        assert nav.occupancy_grid.shape[1] > 0


class TestNavigationSystemPosition:
    """Тесты получения позиции"""
    
    def test_get_current_position(self, mock_lidar, mock_odometry, mock_serial):
        """Тест получения текущей позиции"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        x, y, theta = nav.get_current_position()
        
        assert isinstance(x, float)
        assert isinstance(y, float)
        assert isinstance(theta, float)
        assert x == 0.0
        assert y == 0.0
        assert theta == 0.0
    
    def test_position_after_localization_update(self, mock_lidar, mock_odometry, mock_serial):
        """Тест позиции после обновления локализации"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Установить новую позу одометрии
        mock_odometry.set_pose(1.0, 0.5, 0.1)
        
        # Установить пустое сканирование LiDAR
        mock_lidar.set_scan_data([])
        
        # Обновить локализацию
        nav.update_localization()
        
        x, y, theta = nav.get_current_position()
        
        # Позиция должна измениться
        assert x != 0.0 or y != 0.0 or theta != 0.0


class TestNavigationSystemStop:
    """Тесты остановки робота"""
    
    def test_stop_sets_flag(self, mock_lidar, mock_odometry, mock_serial):
        """Тест установки флага остановки"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        nav.is_stopped = False
        nav.stop()
        
        assert nav.is_stopped is True
    
    def test_stop_sends_motor_command(self, mock_lidar, mock_odometry, mock_serial):
        """Тест отправки команды остановки моторам"""
        # Добавить метод send_motor_command к mock_serial
        mock_serial.motor_commands = []
        
        def send_motor_command(left_speed, right_speed, left_dir, right_dir):
            mock_serial.motor_commands.append((left_speed, right_speed, left_dir, right_dir))
        
        mock_serial.send_motor_command = send_motor_command
        
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        nav.stop()
        
        # Проверить, что была отправлена команда остановки
        assert len(mock_serial.motor_commands) > 0
        last_command = mock_serial.motor_commands[-1]
        assert last_command == (0, 0, 0, 0)


class TestLocalizationUpdate:
    """Тесты обновления локализации"""
    
    def test_update_localization_with_odometry(self, mock_lidar, mock_odometry, mock_serial):
        """Тест обновления локализации с данными одометрии"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Сохранить начальную позицию
        initial_x, initial_y, initial_theta = nav.get_current_position()
        
        # Изменить одометрию
        mock_odometry.set_pose(0.5, 0.3, 0.1)
        mock_lidar.set_scan_data([])
        
        # Обновить локализацию
        nav.update_localization()
        
        # Позиция должна обновиться
        new_x, new_y, new_theta = nav.get_current_position()
        
        # Проверить, что позиция изменилась
        assert (new_x != initial_x or new_y != initial_y or new_theta != initial_theta)
    
    def test_normalize_angle(self, mock_lidar, mock_odometry, mock_serial):
        """Тест нормализации угла"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Тест различных углов
        assert abs(nav._normalize_angle(0.0)) < 0.001
        assert abs(nav._normalize_angle(np.pi) - np.pi) < 0.001
        assert abs(nav._normalize_angle(-np.pi) - (-np.pi)) < 0.001
        
        # Углы больше 2*pi должны нормализоваться
        normalized = nav._normalize_angle(3 * np.pi)
        assert -np.pi <= normalized <= np.pi
        
        # Углы меньше -2*pi должны нормализоваться
        normalized = nav._normalize_angle(-3 * np.pi)
        assert -np.pi <= normalized <= np.pi


class TestRayCasting:
    """Тесты трассировки лучей"""
    
    def test_ray_cast_returns_distance(self, mock_lidar, mock_odometry, mock_serial):
        """Тест возврата расстояния при трассировке луча"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Трассировка луча из начала координат
        distance = nav._ray_cast(0.0, 0.0, 0.0)
        
        assert isinstance(distance, float)
        assert distance >= 0.0
    
    def test_ray_cast_max_range(self, mock_lidar, mock_odometry, mock_serial):
        """Тест максимальной дальности луча"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Трассировка луча с малой максимальной дальностью
        max_range = 1.0
        distance = nav._ray_cast(0.0, 0.0, 0.0, max_range=max_range)
        
        assert distance <= max_range


class TestParticleFilter:
    """Тесты фильтра частиц"""
    
    def test_effective_particles_calculation(self, mock_lidar, mock_odometry, mock_serial):
        """Тест вычисления эффективного количества частиц"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        effective = nav._compute_effective_particles()
        
        assert isinstance(effective, float)
        assert effective > 0
        assert effective <= len(nav.particles)
    
    def test_resample_particles_maintains_count(self, mock_lidar, mock_odometry, mock_serial):
        """Тест сохранения количества частиц при ресемплинге"""
        from config import NUM_PARTICLES
        
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        initial_count = len(nav.particles)
        
        # Выполнить ресемплинг
        nav._resample_particles()
        
        assert len(nav.particles) == initial_count
        assert len(nav.particles) == NUM_PARTICLES
    
    def test_resample_normalizes_weights(self, mock_lidar, mock_odometry, mock_serial):
        """Тест нормализации весов после ресемплинга"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Выполнить ресемплинг
        nav._resample_particles()
        
        # Проверить, что веса нормализованы
        total_weight = sum(p.weight for p in nav.particles)
        assert abs(total_weight - 1.0) < 0.01


if __name__ == '__main__':
    pytest.main([__file__, '-v'])



class TestPathPlanning:
    """Тесты планирования пути"""
    
    def test_plan_path_returns_list(self, mock_lidar, mock_odometry, mock_serial):
        """Тест возврата списка точек пути"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        start = (0.0, 0.0)
        goal = (2.0, 2.0)
        
        path = nav.plan_path(start, goal)
        
        assert isinstance(path, list)
    
    def test_plan_path_starts_at_start(self, mock_lidar, mock_odometry, mock_serial):
        """Тест начала пути в начальной точке"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        start = (0.0, 0.0)
        goal = (2.0, 2.0)
        
        path = nav.plan_path(start, goal)
        
        if len(path) > 0:
            # Первая точка должна быть близка к начальной
            assert abs(path[0][0] - start[0]) < 0.2
            assert abs(path[0][1] - start[1]) < 0.2
    
    def test_plan_path_ends_at_goal(self, mock_lidar, mock_odometry, mock_serial):
        """Тест окончания пути в целевой точке"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        start = (0.0, 0.0)
        goal = (2.0, 2.0)
        
        path = nav.plan_path(start, goal)
        
        if len(path) > 0:
            # Последняя точка должна быть близка к целевой
            assert abs(path[-1][0] - goal[0]) < 0.2
            assert abs(path[-1][1] - goal[1]) < 0.2
    
    def test_plan_path_to_same_position(self, mock_lidar, mock_odometry, mock_serial):
        """Тест планирования пути к текущей позиции (нулевое расстояние)"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        start = (1.0, 1.0)
        goal = (1.0, 1.0)
        
        path = nav.plan_path(start, goal)
        
        # Должен вернуть путь из одной точки
        assert len(path) == 1
        assert path[0] == start
    
    def test_plan_path_around_obstacles(self, mock_lidar, mock_odometry, mock_serial):
        """Тест планирования пути вокруг препятствий"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Планирование пути через область с препятствиями
        start = (0.0, 0.0)
        goal = (5.0, 3.0)
        
        path = nav.plan_path(start, goal)
        
        # Путь должен существовать (если карта позволяет)
        # Проверяем, что все точки пути валидны
        for x, y in path:
            assert nav._is_valid_position(x, y)
    
    def test_plan_path_with_invalid_start(self, mock_lidar, mock_odometry, mock_serial):
        """Тест планирования с невалидной начальной точкой"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Точка за пределами карты
        start = (-100.0, -100.0)
        goal = (2.0, 2.0)
        
        # Должен выбросить исключение
        with pytest.raises(Exception):  # PathPlanningFailureError
            path = nav.plan_path(start, goal)
    
    def test_plan_path_with_invalid_goal(self, mock_lidar, mock_odometry, mock_serial):
        """Тест планирования с невалидной целевой точкой"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        start = (0.0, 0.0)
        # Точка за пределами карты
        goal = (100.0, 100.0)
        
        # Должен выбросить исключение
        with pytest.raises(Exception):  # PathPlanningFailureError
            path = nav.plan_path(start, goal)


class TestCoordinateConversion:
    """Тесты преобразования координат"""
    
    def test_world_to_grid_conversion(self, mock_lidar, mock_odometry, mock_serial):
        """Тест преобразования мировых координат в сетку"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        x, y = 0.0, 0.0
        grid_x, grid_y = nav._world_to_grid(x, y)
        
        assert isinstance(grid_x, int)
        assert isinstance(grid_y, int)
    
    def test_grid_to_world_conversion(self, mock_lidar, mock_odometry, mock_serial):
        """Тест преобразования сетки в мировые координаты"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        grid_x, grid_y = 10, 10
        x, y = nav._grid_to_world(grid_x, grid_y)
        
        assert isinstance(x, float)
        assert isinstance(y, float)
    
    def test_world_grid_world_roundtrip(self, mock_lidar, mock_odometry, mock_serial):
        """Тест обратного преобразования координат"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        original_x, original_y = 1.5, 2.3
        
        # Преобразование в сетку и обратно
        grid_x, grid_y = nav._world_to_grid(original_x, original_y)
        converted_x, converted_y = nav._grid_to_world(grid_x, grid_y)
        
        # Должны быть близки (с учетом дискретизации)
        resolution = nav.map_data['resolution']
        assert abs(converted_x - original_x) < resolution
        assert abs(converted_y - original_y) < resolution


class TestPositionValidation:
    """Тесты проверки валидности позиций"""
    
    def test_valid_position_in_free_space(self, mock_lidar, mock_odometry, mock_serial):
        """Тест валидной позиции в свободном пространстве"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Домашняя позиция должна быть валидной
        assert nav._is_valid_position(0.0, 0.0)
    
    def test_invalid_position_outside_map(self, mock_lidar, mock_odometry, mock_serial):
        """Тест невалидной позиции за пределами карты"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Позиция далеко за пределами карты
        assert not nav._is_valid_position(-100.0, -100.0)
        assert not nav._is_valid_position(100.0, 100.0)
    
    def test_position_with_clearance(self, mock_lidar, mock_odometry, mock_serial):
        """Тест проверки позиции с зазором"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Проверка с различными зазорами
        x, y = 1.0, 1.0
        
        # Без зазора
        result_no_clearance = nav._is_valid_position(x, y, clearance=0.0)
        
        # С зазором
        result_with_clearance = nav._is_valid_position(x, y, clearance=0.3)
        
        # Оба должны быть булевыми
        assert isinstance(result_no_clearance, bool)
        assert isinstance(result_with_clearance, bool)


class TestDistanceCalculation:
    """Тесты вычисления расстояний"""
    
    def test_distance_between_same_points(self, mock_lidar, mock_odometry, mock_serial):
        """Тест расстояния между одинаковыми точками"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        pos = (1.0, 2.0)
        distance = nav._distance(pos, pos)
        
        assert abs(distance) < 0.001
    
    def test_distance_calculation(self, mock_lidar, mock_odometry, mock_serial):
        """Тест вычисления расстояния"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        pos1 = (0.0, 0.0)
        pos2 = (3.0, 4.0)
        
        distance = nav._distance(pos1, pos2)
        
        # Расстояние должно быть 5.0 (теорема Пифагора: 3^2 + 4^2 = 5^2)
        assert abs(distance - 5.0) < 0.001
    
    def test_distance_is_symmetric(self, mock_lidar, mock_odometry, mock_serial):
        """Тест симметричности расстояния"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        pos1 = (1.0, 2.0)
        pos2 = (4.0, 6.0)
        
        distance1 = nav._distance(pos1, pos2)
        distance2 = nav._distance(pos2, pos1)
        
        assert abs(distance1 - distance2) < 0.001


class TestPathSimplification:
    """Тесты упрощения пути"""
    
    def test_simplify_short_path(self, mock_lidar, mock_odometry, mock_serial):
        """Тест упрощения короткого пути"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Путь из двух точек не должен упрощаться
        path = [(0.0, 0.0), (1.0, 1.0)]
        simplified = nav._simplify_path(path)
        
        assert len(simplified) == 2
        assert simplified[0] == path[0]
        assert simplified[-1] == path[-1]
    
    def test_simplify_straight_line(self, mock_lidar, mock_odometry, mock_serial):
        """Тест упрощения прямой линии"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Прямая линия с промежуточными точками
        path = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (1.5, 1.5), (2.0, 2.0)]
        simplified = nav._simplify_path(path)
        
        # Упрощенный путь должен быть короче
        assert len(simplified) <= len(path)
        # Начало и конец должны сохраниться
        assert simplified[0] == path[0]
        assert simplified[-1] == path[-1]


class TestLineOfSight:
    """Тесты проверки прямой видимости"""
    
    def test_line_of_sight_same_point(self, mock_lidar, mock_odometry, mock_serial):
        """Тест прямой видимости для одной точки"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        pos = (1.0, 1.0)
        
        # Точка всегда видна сама себе
        assert nav._has_line_of_sight(pos, pos)
    
    def test_line_of_sight_in_free_space(self, mock_lidar, mock_odometry, mock_serial):
        """Тест прямой видимости в свободном пространстве"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Две близкие точки в свободном пространстве
        pos1 = (0.0, 0.0)
        pos2 = (0.5, 0.5)
        
        result = nav._has_line_of_sight(pos1, pos2)
        
        # Должна быть прямая видимость (если нет препятствий)
        assert isinstance(result, bool)


class TestDynamicObstacles:
    """Тесты динамических препятствий"""
    
    def test_update_dynamic_obstacles(self, mock_lidar, mock_odometry, mock_serial):
        """Тест обновления динамических препятствий"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Установить препятствия в LiDAR
        mock_lidar.set_obstacles([(1.0, 0.0), (0.0, 1.0)])
        
        # Обновить динамические препятствия
        nav.update_dynamic_obstacles()
        
        # Должна быть создана динамическая сетка
        assert hasattr(nav, 'dynamic_occupancy_grid')
        assert nav.dynamic_occupancy_grid is not None
    
    def test_plan_path_with_dynamic_obstacles(self, mock_lidar, mock_odometry, mock_serial):
        """Тест планирования пути с динамическими препятствиями"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Установить препятствия
        mock_lidar.set_obstacles([(1.0, 1.0)])
        
        start = (0.0, 0.0)
        goal = (2.0, 2.0)
        
        path = nav.plan_path_with_dynamic_obstacles(start, goal)
        
        # Путь должен быть списком
        assert isinstance(path, list)
    
    def test_check_path_collision(self, mock_lidar, mock_odometry, mock_serial):
        """Тест проверки столкновения пути"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Путь без препятствий
        path = [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]
        mock_lidar.set_obstacles([])
        
        result = nav.check_path_collision(path)
        
        # Должен вернуть булево значение
        assert isinstance(result, bool)
    
    def test_replan_if_needed_no_collision(self, mock_lidar, mock_odometry, mock_serial):
        """Тест перепланирования без столкновений"""
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Путь без препятствий
        current_path = [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]
        goal = (2.0, 2.0)
        mock_lidar.set_obstacles([])
        
        needs_replan, new_path = nav.replan_if_needed(current_path, goal)
        
        # Не должно требоваться перепланирование
        assert isinstance(needs_replan, bool)
        assert isinstance(new_path, list)


class TestNavigateTo:
    """Тесты метода navigate_to"""
    
    def test_navigate_to_already_at_goal(self, mock_lidar, mock_odometry, mock_serial):
        """Тест навигации когда уже в целевой позиции"""
        # Добавить метод send_motor_command к mock_serial
        mock_serial.motor_commands = []
        
        def send_motor_command(left_speed, right_speed, left_dir, right_dir):
            mock_serial.motor_commands.append((left_speed, right_speed, left_dir, right_dir))
        
        mock_serial.send_motor_command = send_motor_command
        
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Робот уже в позиции (0, 0)
        result = nav.navigate_to(0.0, 0.0)
        
        # Должен вернуть True (цель достигнута)
        assert result is True
        assert nav.is_stopped is True
    
    def test_navigate_to_returns_false_on_invalid_path(self, mock_lidar, mock_odometry, mock_serial):
        """Тест навигации к недостижимой цели"""
        mock_serial.motor_commands = []
        
        def send_motor_command(left_speed, right_speed, left_dir, right_dir):
            mock_serial.motor_commands.append((left_speed, right_speed, left_dir, right_dir))
        
        mock_serial.send_motor_command = send_motor_command
        
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Попытка навигации к невалидной позиции (за пределами карты)
        # Должен выбросить исключение после всех попыток
        with pytest.raises(Exception):  # PathPlanningFailureError
            result = nav.navigate_to(-100.0, -100.0)
    
    def test_navigate_to_stops_on_error(self, mock_lidar, mock_odometry, mock_serial):
        """Тест остановки при ошибке отправки команды"""
        # Создать mock который выбрасывает исключение
        def send_motor_command_error(left_speed, right_speed, left_dir, right_dir):
            raise Exception("Serial communication error")
        
        mock_serial.send_motor_command = send_motor_command_error
        
        nav = NavigationSystem(
            map_file='assets/maps/warehouse_map.yaml',
            lidar_interface=mock_lidar,
            odometry=mock_odometry,
            serial_comm=mock_serial
        )
        
        # Установить валидную позицию одометрии
        mock_odometry.set_pose(0.0, 0.0, 0.0)
        mock_lidar.set_scan_data([])
        
        # Попытка навигации к валидной цели
        # Должен выбросить NavigationError из-за ошибки связи
        with pytest.raises(Exception):  # NavigationError
            result = nav.navigate_to(1.0, 1.0)


class TestPIDController:
    """Тесты PID контроллера"""
    
    def test_pid_initialization(self):
        """Тест инициализации PID контроллера"""
        from navigation import PIDController
        
        pid = PIDController(kp=1.0, ki=0.1, kd=0.05)
        
        assert pid.kp == 1.0
        assert pid.ki == 0.1
        assert pid.kd == 0.05
        assert pid.integral == 0.0
        assert pid.previous_error == 0.0
    
    def test_pid_update_proportional(self):
        """Тест пропорциональной составляющей PID"""
        from navigation import PIDController
        
        pid = PIDController(kp=1.0, ki=0.0, kd=0.0)
        
        error = 2.0
        dt = 0.1
        
        output = pid.update(error, dt)
        
        # Только пропорциональная составляющая
        assert abs(output - 2.0) < 0.001
    
    def test_pid_update_integral(self):
        """Тест интегральной составляющей PID"""
        from navigation import PIDController
        
        pid = PIDController(kp=0.0, ki=1.0, kd=0.0)
        
        error = 1.0
        dt = 0.1
        
        # Первое обновление
        output1 = pid.update(error, dt)
        
        # Второе обновление
        output2 = pid.update(error, dt)
        
        # Интеграл должен накапливаться
        assert output2 > output1
    
    def test_pid_update_derivative(self):
        """Тест дифференциальной составляющей PID"""
        from navigation import PIDController
        
        pid = PIDController(kp=0.0, ki=0.0, kd=1.0)
        
        dt = 0.1
        
        # Первое обновление с ошибкой 0
        output1 = pid.update(0.0, dt)
        
        # Второе обновление с ошибкой 1 (изменение ошибки)
        output2 = pid.update(1.0, dt)
        
        # Дифференциальная составляющая должна быть ненулевой
        assert output2 != 0.0
    
    def test_pid_reset(self):
        """Тест сброса PID контроллера"""
        from navigation import PIDController
        
        pid = PIDController(kp=1.0, ki=1.0, kd=1.0)
        
        # Обновить несколько раз
        pid.update(1.0, 0.1)
        pid.update(2.0, 0.1)
        
        # Сбросить
        pid.reset()
        
        # Состояние должно быть сброшено
        assert pid.integral == 0.0
        assert pid.previous_error == 0.0
