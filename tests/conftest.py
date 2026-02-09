# -*- coding: utf-8 -*-
"""
Конфигурация pytest и общие фикстуры для тестов RelayBot
"""

import os
import sys
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

# Добавить корневую директорию проекта в путь Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Импорт моделей базы данных
from db.db_models import Base, Customer, Order


# ============================================================================
# ФИКСТУРЫ БАЗЫ ДАННЫХ
# ============================================================================

@pytest.fixture(scope='session')
def test_db_engine():
    """
    Создать временный движок базы данных для тестов
    Используется на уровне сессии для всех тестов
    """
    # Создать временную базу данных в памяти
    engine = create_engine('sqlite:///:memory:', echo=False)
    
    # Создать все таблицы
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Очистка после всех тестов
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope='function')
def test_db_session(test_db_engine):
    """
    Создать сессию базы данных для каждого теста
    Автоматически откатывает изменения после теста
    """
    # Создать фабрику сессий
    Session = sessionmaker(bind=test_db_engine)
    session = Session()
    
    yield session
    
    # Откатить все изменения и закрыть сессию
    session.rollback()
    session.close()


@pytest.fixture(scope='function')
def test_db_with_data(test_db_session):
    """
    Создать базу данных с тестовыми данными
    Включает клиентов и заказы для тестирования
    """
    # Создать тестовых клиентов
    customer1 = Customer(
        id=1,
        name="Иван",
        surname="Иванов",
        phone=79001234567,
        secret_key="SECRET123"
    )
    
    customer2 = Customer(
        id=2,
        name="Мария",
        surname="Петрова",
        phone=79009876543,
        secret_key="KEY456ABC"
    )
    
    customer3 = Customer(
        id=3,
        name="Алексей",
        surname="Сидоров",
        phone=79005555555,
        secret_key="TESTKEY789"
    )
    
    # Создать тестовые заказы
    order1 = Order(id=1, customer_id=1)
    order2 = Order(id=2, customer_id=2)
    order3 = Order(id=3, customer_id=3)
    order4 = Order(id=4, customer_id=1)  # Второй заказ для первого клиента
    
    # Добавить в базу данных
    test_db_session.add_all([customer1, customer2, customer3])
    test_db_session.add_all([order1, order2, order3, order4])
    test_db_session.commit()
    
    yield test_db_session


# ============================================================================
# ФИКСТУРЫ ДЛЯ MOCK ОБЪЕКТОВ
# ============================================================================

class MockSerial:
    """Mock объект для последовательной связи с Arduino"""
    
    def __init__(self):
        self.commands_sent = []
        self.responses = []
        self.is_open = True
    
    def write(self, data):
        """Записать данные в mock serial"""
        self.commands_sent.append(data.decode('utf-8') if isinstance(data, bytes) else data)
    
    def readline(self):
        """Прочитать строку из mock serial"""
        if self.responses:
            return self.responses.pop(0).encode('utf-8')
        return b''
    
    def in_waiting(self):
        """Количество байт в буфере"""
        return len(self.responses)
    
    def close(self):
        """Закрыть соединение"""
        self.is_open = False
    
    def add_response(self, response):
        """Добавить ответ для чтения"""
        self.responses.append(response)
    
    def get_last_command(self):
        """Получить последнюю отправленную команду"""
        return self.commands_sent[-1] if self.commands_sent else None
    
    def clear_commands(self):
        """Очистить список команд"""
        self.commands_sent = []


@pytest.fixture
def mock_serial():
    """Фикстура для mock последовательной связи"""
    return MockSerial()


class MockLiDAR:
    """Mock объект для LiDAR сенсора"""
    
    def __init__(self):
        self.scan_data = []
        self.obstacles = []
        self.is_connected = True
    
    def get_scan(self):
        """Получить текущее сканирование"""
        return self.scan_data
    
    def set_scan_data(self, data):
        """Установить данные сканирования для тестов"""
        self.scan_data = data
    
    def detect_person(self):
        """Mock обнаружение человека"""
        return None
    
    def get_obstacles(self, min_distance=0.3):
        """Mock получение препятствий"""
        return self.obstacles
    
    def set_obstacles(self, obstacles):
        """Установить препятствия для тестов"""
        self.obstacles = obstacles


@pytest.fixture
def mock_lidar():
    """Фикстура для mock LiDAR"""
    return MockLiDAR()


class MockOdometry:
    """Mock объект для системы одометрии"""
    
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
    
    def update(self, left_ticks, right_ticks, dt):
        """Mock обновление одометрии"""
        pass
    
    def get_pose(self):
        """Получить текущую позу"""
        return (self.x, self.y, self.theta)
    
    def reset(self, x=0.0, y=0.0, theta=0.0):
        """Сбросить одометрию"""
        self.x = x
        self.y = y
        self.theta = theta
    
    def set_pose(self, x, y, theta):
        """Установить позу для тестов"""
        self.x = x
        self.y = y
        self.theta = theta


@pytest.fixture
def mock_odometry():
    """Фикстура для mock одометрии"""
    return MockOdometry()


class MockAudioSystem:
    """Mock объект для аудио системы"""
    
    def __init__(self):
        self.played_files = []
    
    def play(self, audio_file, blocking=False):
        """Mock воспроизведение аудио"""
        self.played_files.append(audio_file)
    
    def request_qr_code(self):
        """Mock запрос QR кода"""
        self.played_files.append('request_qr.wav')
    
    def announce_order_accepted(self):
        """Mock объявление принятия заказа"""
        self.played_files.append('order_accepted.wav')
    
    def announce_order_rejected(self):
        """Mock объявление отклонения заказа"""
        self.played_files.append('order_rejected.wav')
    
    def announce_order_number(self, order_id):
        """Mock объявление номера заказа"""
        self.played_files.append(f'order_{order_id}.wav')
    
    def greet_delivery(self):
        """Mock приветствие при доставке"""
        self.played_files.append('delivery_greeting.wav')
    
    def stop(self):
        """Mock остановка воспроизведения"""
        pass
    
    def get_played_files(self):
        """Получить список воспроизведенных файлов"""
        return self.played_files
    
    def clear_played_files(self):
        """Очистить список воспроизведенных файлов"""
        self.played_files = []


@pytest.fixture
def mock_audio():
    """Фикстура для mock аудио системы"""
    return MockAudioSystem()


# ============================================================================
# ФИКСТУРЫ ДЛЯ ТЕСТОВЫХ ДАННЫХ
# ============================================================================

@pytest.fixture
def valid_qr_data():
    """Валидные данные QR кода для тестов"""
    return {
        'order_id': 1,
        'secret_key': 'SECRET123'
    }


@pytest.fixture
def valid_qr_json(valid_qr_data):
    """Валидный JSON QR кода"""
    return json.dumps(valid_qr_data)


@pytest.fixture
def invalid_qr_data():
    """Невалидные данные QR кода для тестов"""
    return [
        '{"invalid": "json"}',  # Отсутствуют обязательные поля
        '{"order_id": 999, "secret_key": "WRONG"}',  # Неверный secret_key
        '{"order_id": "not_a_number", "secret_key": "KEY"}',  # Неверный тип
        'not json at all',  # Невалидный JSON
        '',  # Пустая строка
    ]


@pytest.fixture
def test_positions():
    """Тестовые позиции для навигации"""
    return {
        'home': (0.0, 0.0),
        'warehouse': (5.0, 3.0),
        'customer1': (1.5, 1.0),
        'customer2': (-1.0, 2.0),
        'customer3': (2.0, -1.5),
    }


@pytest.fixture
def test_map_file(tmp_path):
    """Создать временный файл карты для тестов"""
    map_data = {
        'resolution': 0.05,
        'width': 10.0,
        'height': 10.0,
        'origin': [0.0, 0.0],
        'obstacles': [
            {'x': 3.0, 'y': 3.0, 'width': 1.0, 'height': 1.0},
            {'x': 7.0, 'y': 2.0, 'width': 0.5, 'height': 2.0},
        ]
    }
    
    import yaml
    map_file = tmp_path / "test_map.yaml"
    with open(map_file, 'w') as f:
        yaml.dump(map_data, f)
    
    return str(map_file)


# ============================================================================
# ФИКСТУРЫ ДЛЯ HYPOTHESIS (PROPERTY-BASED TESTING)
# ============================================================================

@pytest.fixture
def hypothesis_settings():
    """Настройки для Hypothesis тестов"""
    from hypothesis import settings, Phase
    
    return settings(
        max_examples=100,  # Минимум 100 итераций
        phases=[Phase.explicit, Phase.reuse, Phase.generate, Phase.target],
        deadline=None,  # Отключить таймаут для медленных тестов
    )


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def create_test_customer(session, customer_id=1, name="Тест", surname="Тестов", 
                        phone=79000000000, secret_key="TESTKEY"):
    """
    Создать тестового клиента в базе данных
    
    Args:
        session: Сессия базы данных
        customer_id: ID клиента
        name: Имя
        surname: Фамилия
        phone: Телефон
        secret_key: Секретный ключ
    
    Returns:
        Customer: Созданный клиент
    """
    customer = Customer(
        id=customer_id,
        name=name,
        surname=surname,
        phone=phone,
        secret_key=secret_key
    )
    session.add(customer)
    session.commit()
    return customer


def create_test_order(session, order_id=1, customer_id=1):
    """
    Создать тестовый заказ в базе данных
    
    Args:
        session: Сессия базы данных
        order_id: ID заказа
        customer_id: ID клиента
    
    Returns:
        Order: Созданный заказ
    """
    order = Order(id=order_id, customer_id=customer_id)
    session.add(order)
    session.commit()
    return order


# Экспортировать вспомогательные функции
__all__ = [
    'test_db_engine',
    'test_db_session',
    'test_db_with_data',
    'mock_serial',
    'mock_lidar',
    'mock_odometry',
    'mock_audio',
    'valid_qr_data',
    'valid_qr_json',
    'invalid_qr_data',
    'test_positions',
    'test_map_file',
    'hypothesis_settings',
    'create_test_customer',
    'create_test_order',
]
