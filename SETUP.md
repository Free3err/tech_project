# RelayBot - Настройка проекта

Этот документ описывает настройку инфраструктуры проекта RelayBot.

## Структура проекта

```
relaybot/
├── config.py                    # Конфигурация системы (НОВЫЙ)
├── main.py                      # Главный файл
├── state_machine.py             # Машина состояний (TODO)
├── navigation.py                # Система навигации (TODO)
├── lidar_interface.py           # Интерфейс LiDAR (TODO)
├── odometry.py                  # Система одометрии (TODO)
├── audio_system.py              # Аудио система (TODO)
├── box_controller.py            # Контроллер коробки (TODO)
├── qrScanner.py                 # QR сканер (существующий)
├── serialConnection.py          # Последовательная связь (существующий)
├── ideal_program.ino            # Arduino код (существующий)
├── requirements.txt             # Зависимости Python (ОБНОВЛЕН)
│
├── db/                          # База данных
│   ├── db.py
│   ├── db_models.py
│   └── functions.py
│
├── assets/                      # Ресурсы
│   ├── audio/                   # Аудио файлы (НОВАЯ ДИРЕКТОРИЯ)
│   │   ├── .gitkeep
│   │   ├── successScan.wav      # (существующий)
│   │   └── failureScan.wav      # (существующий)
│   ├── maps/                    # Карты окружения (НОВАЯ ДИРЕКТОРИЯ)
│   │   └── .gitkeep
│   └── orders.db                # База данных заказов
│
└── tests/                       # Тесты (НОВАЯ ДИРЕКТОРИЯ)
    ├── __init__.py
    ├── conftest.py              # Фикстуры pytest
    ├── README.md                # Документация тестов
    ├── unit/                    # Модульные тесты
    │   ├── __init__.py
    │   └── test_config.py       # Тесты конфигурации
    ├── property/                # Property-based тесты
    │   └── __init__.py
    └── integration/             # Интеграционные тесты
        └── __init__.py
```

## Установка зависимостей

### 1. Обновить pip

```bash
python -m pip install --upgrade pip
```

### 2. Установить зависимости

```bash
pip install -r requirements.txt
```

### Новые зависимости

В `requirements.txt` добавлены следующие пакеты:

- **hypothesis>=6.0.0** - Property-based тестирование
- **pytest>=7.0.0** - Фреймворк тестирования
- **scipy>=1.7.0** - Научные вычисления (фильтр частиц)

Существующие зависимости сохранены:
- numpy, opencv-python, playsound3, pyserial, PyYAML, SQLAlchemy

## Конфигурация (config.py)

Файл `config.py` содержит все параметры системы:

### Координаты зон
- `HOME_POSITION` - домашняя позиция (0, 0)
- `WAREHOUSE_ZONE` - зона склада (5.0, 3.0)
- `DELIVERY_ZONE_RADIUS` - радиус зоны доставки

### Параметры навигации
- `POSITION_TOLERANCE` - допуск позиции (10 см)
- `CUSTOMER_APPROACH_DISTANCE` - расстояние подхода (50 см)
- `MAX_SPEED` - максимальная скорость моторов

### Параметры LiDAR
- `LIDAR_PORT` - порт LiDAR (/dev/ttyUSB0)
- `LIDAR_BAUDRATE` - скорость передачи (230400)
- `PERSON_DETECTION_MIN_POINTS` - минимум точек для обнаружения

### Параметры одометрии
- `WHEEL_BASE` - расстояние между колесами (25 см)
- `WHEEL_RADIUS` - радиус колеса (5 см)
- `ENCODER_TICKS_PER_REVOLUTION` - тики на оборот (360)

### Параметры последовательной связи
- `ARDUINO_PORT` - порт Arduino (COM10 / /dev/ttyACM0)
- `ARDUINO_BAUDRATE` - скорость передачи (9600)

### Параметры доставки
- `DELIVERY_TIMEOUT` - таймаут доставки (10 сек)
- `LOADING_CONFIRMATION_TIMEOUT` - таймаут загрузки (60 сек)
- `QR_SCAN_TIMEOUT` - таймаут сканирования (30 сек)

### Другие параметры
- Аудио система
- База данных
- Сервопривод
- Карты
- Фильтр частиц
- Планирование пути
- PID контроллер
- Логирование
- Восстановление после ошибок

## Тестирование

### Структура тестов

- **tests/unit/** - Модульные тесты для отдельных компонентов
- **tests/property/** - Property-based тесты с Hypothesis
- **tests/integration/** - Интеграционные тесты полной системы

### Фикстуры (conftest.py)

Файл `tests/conftest.py` содержит:

#### Фикстуры базы данных
- `test_db_engine` - временная БД в памяти
- `test_db_session` - сессия БД для каждого теста
- `test_db_with_data` - БД с тестовыми данными

#### Mock объекты
- `mock_serial` - mock последовательной связи
- `mock_lidar` - mock LiDAR сенсора
- `mock_odometry` - mock одометрии
- `mock_audio` - mock аудио системы

#### Тестовые данные
- `valid_qr_data` - валидные данные QR
- `invalid_qr_data` - невалидные данные QR
- `test_positions` - тестовые позиции
- `test_map_file` - временный файл карты

### Запуск тестов

```bash
# Все тесты
pytest tests/

# Только модульные тесты
pytest tests/unit/

# С подробным выводом
pytest tests/ -v

# С покрытием кода
pytest tests/ --cov=. --cov-report=html
```

### Пример теста

```python
def test_navigation_to_home():
    """
    Тест навигации к домашней позиции
    Requirements: 1.1, 8.2
    """
    nav = NavigationSystem(...)
    result = nav.navigate_to(0.0, 0.0)
    assert result == True
    pos = nav.get_current_position()
    assert abs(pos[0]) < 0.1  # В пределах 10 см
    assert abs(pos[1]) < 0.1
```

## Директории ресурсов

### assets/audio/

Директория для аудио файлов. Необходимо создать:

- `request_qr.wav` - "Пожалуйста, покажите QR код вашего заказа"
- `order_accepted.wav` - "Заказ принят. Еду на склад."
- `order_rejected.wav` - "Заказ не найден. Пожалуйста, проверьте QR код."
- `delivery_greeting.wav` - "Ваш заказ доставлен. Приятного дня!"
- `error.wav` - Звук ошибки

Опционально:
- `order_1.wav` ... `order_100.wav` - Объявления номеров заказов

### assets/maps/

Директория для файлов карт окружения. Необходимо создать:

- `warehouse_map.yaml` - Карта склада и зоны доставки

Формат файла карты:
```yaml
resolution: 0.05  # метры на пиксель
width: 10.0       # метры
height: 10.0      # метры
origin: [0.0, 0.0]
obstacles:
  - {x: 3.0, y: 3.0, width: 1.0, height: 1.0}
  - {x: 7.0, y: 2.0, width: 0.5, height: 2.0}
```

## Следующие шаги

После настройки инфраструктуры, следующие задачи:

1. **Task 2** - Расширить последовательную связь (serialConnection.py)
2. **Task 3** - Создать структуры данных (navigation.py)
3. **Task 4** - Реализовать систему одометрии (odometry.py)
4. **Task 5** - Реализовать интерфейс LiDAR (lidar_interface.py)
5. **Task 7-9** - Реализовать систему навигации
6. **Task 11** - Реализовать аудио систему
7. **Task 12** - Реализовать контроллер коробки
8. **Task 13** - Расширить систему проверки заказов
9. **Task 15-25** - Реализовать машину состояний
10. **Task 27** - Расширить Arduino код
11. **Task 28** - Обновить main.py

## Проверка установки

Запустить тесты конфигурации:

```bash
pytest tests/unit/test_config.py -v
```

Все тесты должны пройти успешно, подтверждая правильность настройки.

## Требования к оборудованию

- Raspberry Pi (3B+ или новее)
- Arduino (Uno, Mega, или совместимый)
- LDROBOT D500 LiDAR
- USB камера для QR сканирования
- Моторы с энкодерами
- Сервопривод для коробки
- IR сенсор расстояния
- LED для глаз робота

## Требования к ПО

- Python 3.7+
- Arduino IDE (для загрузки кода на Arduino)
- Операционная система: Windows или Linux (Raspberry Pi OS)

## Поддержка

Для вопросов и проблем см. документацию в:
- `.kiro/specs/relaybot-autonomous-delivery/requirements.md`
- `.kiro/specs/relaybot-autonomous-delivery/design.md`
- `.kiro/specs/relaybot-autonomous-delivery/tasks.md`
