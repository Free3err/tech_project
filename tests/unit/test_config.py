# -*- coding: utf-8 -*-
"""
Модульные тесты для конфигурации системы
"""

import pytest
import sys
import os

# Добавить корневую директорию в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import config


def test_config_home_position():
    """
    Тест: домашняя позиция должна быть (0, 0)
    Requirements: 1.1
    """
    assert config.HOME_POSITION == (0.0, 0.0), "Домашняя позиция должна быть в начале координат"


def test_config_warehouse_zone():
    """
    Тест: зона склада должна быть определена
    Requirements: 4.1
    """
    assert config.WAREHOUSE_ZONE is not None, "Зона склада должна быть определена"
    assert len(config.WAREHOUSE_ZONE) == 2, "Зона склада должна иметь координаты (x, y)"
    assert isinstance(config.WAREHOUSE_ZONE[0], (int, float)), "X координата должна быть числом"
    assert isinstance(config.WAREHOUSE_ZONE[1], (int, float)), "Y координата должна быть числом"


def test_config_position_tolerance():
    """
    Тест: допуск позиции должен быть 10 см (0.1 м)
    Requirements: 1.4, 9.2
    """
    assert config.POSITION_TOLERANCE == 0.1, "Допуск позиции должен быть 10 см"


def test_config_customer_approach_distance():
    """
    Тест: расстояние подхода к клиенту должно быть 50 см (0.5 м)
    Requirements: 2.6
    """
    assert config.CUSTOMER_APPROACH_DISTANCE == 0.5, "Расстояние подхода должно быть 50 см"


def test_config_delivery_timeout():
    """
    Тест: таймаут доставки должен быть 10 секунд
    Requirements: 7.3
    """
    assert config.DELIVERY_TIMEOUT == 10.0, "Таймаут доставки должен быть 10 секунд"


def test_config_qr_scan_timeout():
    """
    Тест: таймаут сканирования QR должен быть 30 секунд
    Requirements: 3.6
    """
    assert config.QR_SCAN_TIMEOUT == 30.0, "Таймаут сканирования QR должен быть 30 секунд"


def test_config_loading_timeout():
    """
    Тест: таймаут загрузки должен быть 60 секунд
    Requirements: 5.4
    """
    assert config.LOADING_CONFIRMATION_TIMEOUT == 60.0, "Таймаут загрузки должен быть 60 секунд"


def test_config_box_angles():
    """
    Тест: углы коробки должны быть корректными
    Requirements: 15.1, 15.2
    """
    assert config.BOX_OPEN_ANGLE == 90, "Угол открытой коробки должен быть 90 градусов"
    assert config.BOX_CLOSE_ANGLE == 0, "Угол закрытой коробки должен быть 0 градусов"


def test_config_wheel_parameters():
    """
    Тест: параметры колес должны быть определены
    Requirements: 11.5
    """
    assert config.WHEEL_BASE > 0, "Расстояние между колесами должно быть положительным"
    assert config.WHEEL_RADIUS > 0, "Радиус колеса должен быть положительным"
    assert config.ENCODER_TICKS_PER_REVOLUTION > 0, "Количество тиков энкодера должно быть положительным"


def test_config_lidar_parameters():
    """
    Тест: параметры LiDAR должны быть определены
    Requirements: 11.1
    """
    assert config.LIDAR_PORT is not None, "Порт LiDAR должен быть определен"
    assert config.LIDAR_BAUDRATE > 0, "Скорость передачи LiDAR должна быть положительной"
    assert config.LIDAR_MAX_RANGE > 0, "Максимальная дальность LiDAR должна быть положительной"


def test_config_serial_parameters():
    """
    Тест: параметры последовательной связи должны быть определены
    Requirements: 12.1
    """
    assert config.ARDUINO_PORT is not None, "Порт Arduino должен быть определен"
    assert config.ARDUINO_BAUDRATE == 9600, "Скорость передачи Arduino должна быть 9600"


def test_config_update_rates():
    """
    Тест: частоты обновления должны быть >= 10 Гц
    Requirements: 9.7, 11.1
    """
    assert config.LOCALIZATION_UPDATE_RATE >= 10, "Частота локализации должна быть >= 10 Гц"
    assert config.NAVIGATION_UPDATE_RATE >= 10, "Частота навигации должна быть >= 10 Гц"


def test_config_audio_directory():
    """
    Тест: директория аудио должна быть определена
    Requirements: 13.1
    """
    assert config.AUDIO_DIR is not None, "Директория аудио должна быть определена"
    assert isinstance(config.AUDIO_DIR, str), "Директория аудио должна быть строкой"


def test_config_database_url():
    """
    Тест: URL базы данных должен быть определен
    Requirements: 3.4
    """
    assert config.DATABASE_URL is not None, "URL базы данных должен быть определен"
    assert 'sqlite' in config.DATABASE_URL.lower(), "База данных должна быть SQLite"


def test_config_map_file():
    """
    Тест: файл карты должен быть определен
    Requirements: 9.6
    """
    assert config.MAP_FILE is not None, "Файл карты должен быть определен"
    assert config.MAP_FILE.endswith('.yaml'), "Файл карты должен быть YAML"


def test_config_particle_filter_parameters():
    """
    Тест: параметры фильтра частиц должны быть определены
    Requirements: 9.6
    """
    assert config.NUM_PARTICLES > 0, "Количество частиц должно быть положительным"
    assert config.NUM_PARTICLES >= 100, "Количество частиц должно быть >= 100 для точности"
    assert config.MOTION_NOISE_TRANSLATION > 0, "Шум движения должен быть положительным"
    assert config.MOTION_NOISE_ROTATION > 0, "Шум вращения должен быть положительным"


def test_config_obstacle_clearance():
    """
    Тест: зазор от препятствий должен быть 30 см
    Requirements: 4.3, 6.3
    """
    assert config.OBSTACLE_CLEARANCE == 0.3, "Зазор от препятствий должен быть 30 см"


def test_config_state_timeouts():
    """
    Тест: таймауты состояний должны быть определены
    Requirements: 10.3
    """
    assert config.STATE_TIMEOUT_VERIFYING == 30.0, "Таймаут VERIFYING должен быть 30 секунд"
    assert config.STATE_TIMEOUT_LOADING == 60.0, "Таймаут LOADING должен быть 60 секунд"
    assert config.STATE_TIMEOUT_DELIVERING == 15.0, "Таймаут DELIVERING должен быть 15 секунд"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
