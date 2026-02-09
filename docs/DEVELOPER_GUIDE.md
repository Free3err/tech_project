# RelayBot - Руководство разработчика

**Версия:** 1.0  
**Дата:** 09.02.2026

---

## Содержание

1. [Архитектура системы](#архитектура-системы)
2. [Модули и интерфейсы](#модули-и-интерфейсы)
3. [Машина состояний](#машина-состояний)
4. [Система навигации](#система-навигации)
5. [Тестирование](#тестирование)
6. [Расширение функциональности](#расширение-функциональности)

---

## Архитектура системы

### Общая структура

RelayBot построен на модульной архитектуре с четким разделением ответственности:

```
┌─────────────────────────────────────────────────┐
│              main.py (Orchestrator)             │
└────────────────────┬────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │   StateMachine        │
         │   (Координатор)       │
         └───────────┬───────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
┌───▼────┐    ┌─────▼─────┐   ┌─────▼──────┐
│Navigation│   │OrderVerif │   │BoxControl  │
└───┬────┘    └─────┬─────┘   └─────┬──────┘
    │               │               │
┌───▼───┐    ┌─────▼─────┐   ┌─────▼──────┐
│LiDAR  │    │QRScanner  │   │SerialComm  │
│Odom   │    │Database   │   │Arduino     │
└───────┘    └───────────┘   └────────────┘
```


### Слои системы

**Слой 1: Аппаратное взаимодействие**
- `serialConnection.py` - Связь с Arduino
- `lidar_interface.py` - Интерфейс LiDAR
- `qrScanner.py` - Сканирование QR кодов

**Слой 2: Обработка данных**
- `odometry.py` - Расчет позиции по энкодерам
- `navigation.py` - Локализация и планирование пути
- `db/` - Работа с базой данных

**Слой 3: Управление**
- `box_controller.py` - Управление коробкой
- `audio_system.py` - Аудио обратная связь
- `state_machine.py` - Логика поведения

**Слой 4: Оркестрация**
- `main.py` - Инициализация и главный цикл
- `config.py` - Централизованная конфигурация

---

## Модули и интерфейсы

### config.py

Централизованная конфигурация всех параметров системы.

**Основные секции:**
- Координаты зон (HOME, WAREHOUSE, DELIVERY_ZONE)
- Параметры навигации (скорость, допуски, частота обновления)
- Параметры сенсоров (LiDAR, энкодеры, IR)
- Параметры связи (порты, скорости, таймауты)
- Параметры доставки (таймауты состояний)
- Параметры аудио и базы данных

**Использование:**
```python
import config

# Доступ к параметрам
max_speed = config.MAX_SPEED
home_pos = config.HOME_POSITION
```

### serialConnection.py

Модуль последовательной связи с Arduino.

**Основные функции:**
```python
# Инициализация
init_serial(port='/dev/ttyACM0', baudrate=9600)

# Отправка команд моторов
send_motor_command(left_speed, right_speed, left_dir, right_dir)

# Управление сервоприводом
send_servo_command(angle)

# Управление LED
send_led_command(command)  # LED_IDLE, LED_MOVING, LED_WAITING, LED_ERROR

# Чтение данных сенсоров
data = read_sensor_data()  # Возвращает dict с encoder_left, encoder_right, ir_distance
```

**Протокол команд:**
- `MOTOR:L_SPEED,R_SPEED,L_DIR,R_DIR\n`
- `SERVO:ANGLE\n`
- `LED:COMMAND\n`

**Протокол ответов:**
- `ENCODER:LEFT,RIGHT\n`
- `IR:DISTANCE\n`
- `ACK\n`


### odometry.py

Система одометрии для отслеживания позиции робота.

**Класс OdometrySystem:**
```python
class OdometrySystem:
    def __init__(self, wheel_base: float, wheel_radius: float):
        """
        Args:
            wheel_base: Расстояние между колесами (м)
            wheel_radius: Радиус колеса (м)
        """
    
    def update(self, left_ticks: int, right_ticks: int, dt: float) -> None:
        """
        Обновление позиции на основе тиков энкодеров
        
        Args:
            left_ticks: Тики левого энкодера
            right_ticks: Тики правого энкодера
            dt: Временной интервал (секунды)
        """
    
    def get_pose(self) -> Tuple[float, float, float]:
        """Возвращает (x, y, theta) в метрах и радианах"""
    
    def reset(self, x: float, y: float, theta: float) -> None:
        """Сброс позиции"""
```

**Кинематика:**
- Использует дифференциальную кинематику
- Вычисляет линейную и угловую скорость
- Интегрирует для получения позиции

### lidar_interface.py

Интерфейс для LiDAR LDROBOT D500.

**Класс LiDARInterface:**
```python
class LiDARInterface:
    def __init__(self, port: str, baudrate: int = 230400):
        """Подключение к LiDAR"""
    
    def get_scan(self) -> List[ScanPoint]:
        """
        Получение сканирования
        
        Returns:
            Список ScanPoint(distance, angle, intensity)
        """
    
    def detect_person(self) -> Optional[Tuple[float, float]]:
        """
        Обнаружение человека
        
        Returns:
            (x, y) относительно робота или None
        """
    
    def get_obstacles(self, min_distance: float) -> List[Tuple[float, float]]:
        """
        Получение препятствий ближе min_distance
        
        Returns:
            Список (x, y) координат препятствий
        """
```

**Алгоритм обнаружения человека:**
1. Фильтрация шума (расстояние 0.1-5 м)
2. Кластеризация точек (расстояние < 0.3 м)
3. Фильтрация по размеру кластера (0.3-0.8 м)
4. Возврат центра ближайшего кластера


### navigation.py

Система навигации с локализацией и планированием пути.

**Класс NavigationSystem:**
```python
class NavigationSystem:
    def __init__(self, map_file: str, lidar_interface, odometry, serial_comm):
        """
        Инициализация с картой окружения
        
        Args:
            map_file: Путь к YAML файлу карты
            lidar_interface: Интерфейс LiDAR
            odometry: Система одометрии
            serial_comm: Модуль последовательной связи
        """
    
    def update_localization(self) -> None:
        """
        Обновление локализации (фильтр частиц)
        Вызывается в главном цикле с частотой 10 Гц
        """
    
    def get_current_position(self) -> Tuple[float, float, float]:
        """Возвращает текущую позицию (x, y, theta)"""
    
    def navigate_to(self, target_x: float, target_y: float) -> bool:
        """
        Навигация к целевой точке
        
        Args:
            target_x, target_y: Целевые координаты (м)
        
        Returns:
            True если цель достигнута, False при ошибке
        """
    
    def stop(self) -> None:
        """Экстренная остановка"""
```

**Компоненты навигации:**

1. **Локализация (Particle Filter):**
   - 200 частиц для оценки позиции
   - Предсказание на основе одометрии
   - Обновление на основе LiDAR сканирования
   - Ресемплинг при низкой эффективности

2. **Планирование пути (A*):**
   - Сетка с разрешением 5 см
   - Эвристика: Евклидово расстояние
   - Зазор от препятствий: 30 см
   - Динамическое переplanирование при обнаружении препятствий

3. **Управление (PID):**
   - Отдельные PID для линейной и угловой скорости
   - Коэффициенты настраиваются в config.py
   - Следование по waypoints с допуском 10 см

### audio_system.py

Система аудио обратной связи.

**Класс AudioSystem:**
```python
class AudioSystem:
    def __init__(self, audio_dir: str = 'assets/audio'):
        """Инициализация с директорией аудио файлов"""
    
    def play(self, audio_file: str, blocking: bool = True) -> None:
        """Воспроизведение аудио файла"""
    
    def request_qr_code(self) -> None:
        """Запрос QR кода у клиента"""
    
    def announce_order_accepted(self) -> None:
        """Объявление принятия заказа"""
    
    def announce_order_rejected(self) -> None:
        """Объявление отклонения заказа"""
    
    def announce_order_number(self, order_id: int) -> None:
        """Объявление номера заказа на складе"""
    
    def greet_delivery(self) -> None:
        """Приветствие при доставке"""
```

**Аудио файлы:**
- `request_qr.wav` - Запрос QR кода
- `order_accepted.wav` - Заказ принят
- `order_rejected.wav` - Заказ отклонен
- `delivery_greeting.wav` - Приветствие доставки
- `order_1.wav` ... `order_100.wav` - Номера заказов


### box_controller.py

Контроллер механизма коробки.

**Класс BoxController:**
```python
class BoxController:
    def __init__(self, serial_comm):
        """Инициализация с модулем последовательной связи"""
    
    def open(self) -> None:
        """Открытие коробки (90°)"""
    
    def close(self) -> None:
        """Закрытие коробки (0°)"""
    
    def is_open(self) -> bool:
        """Проверка состояния коробки"""
    
    def emergency_close(self) -> None:
        """Экстренное закрытие без проверок"""
```

**Особенности:**
- Плавное движение сервопривода (45°/сек)
- Отслеживание текущего состояния
- Обработка ошибок сервопривода

### qrScanner.py

Система проверки заказов через QR коды.

**Класс OrderVerificationSystem:**
```python
class OrderVerificationSystem:
    def __init__(self, db_session, serial_comm):
        """Инициализация с сессией БД и последовательной связью"""
    
    def start_scanning(self, callback: Callable[[bool, Optional[int]], None]) -> None:
        """
        Запуск сканирования QR кодов
        
        Args:
            callback: Функция вызываемая при результате (is_valid, order_id)
        """
    
    def stop_scanning(self) -> None:
        """Остановка сканирования"""
    
    def verify_order(self, order_data: dict) -> Tuple[bool, Optional[int]]:
        """
        Проверка заказа в базе данных
        
        Args:
            order_data: Данные из QR кода (JSON)
        
        Returns:
            (is_valid, order_id)
        """
```

**Формат QR кода:**
```json
{
  "order_id": 123
}
```

---

## Машина состояний

### Архитектура

Машина состояний координирует все подсистемы и управляет поведением робота.

**Состояния:**
1. **WAITING** - Ожидание клиента
2. **APPROACHING** - Подход к клиенту
3. **VERIFYING** - Проверка заказа
4. **NAVIGATING_TO_WAREHOUSE** - Движение к складу
5. **LOADING** - Загрузка посылки
6. **RETURNING_TO_CUSTOMER** - Возврат к клиенту
7. **DELIVERING** - Доставка посылки
8. **RESETTING** - Возврат домой
9. **ERROR_RECOVERY** - Восстановление после ошибки
10. **EMERGENCY_STOP** - Экстренная остановка


### Диаграмма переходов

```
    ┌─────────┐
    │ WAITING │◄──────────────────────────┐
    └────┬────┘                           │
         │ person_detected               │
         ▼                                │
  ┌─────────────┐                   ┌────┴────┐
  │ APPROACHING │                   │RESETTING│
  └──────┬──────┘                   └────▲────┘
         │ reached_customer              │
         ▼                                │
   ┌──────────┐                          │
   │VERIFYING │                          │
   └─────┬────┘                          │
         │ order_valid            delivery_complete
         ▼                                │
┌────────────────────┐            ┌──────┴─────┐
│NAVIGATING_TO_      │            │ DELIVERING │
│WAREHOUSE           │            └──────▲─────┘
└─────────┬──────────┘                   │
          │ reached_warehouse            │
          ▼                               │
     ┌────────┐                    ┌─────┴──────────┐
     │LOADING │                    │RETURNING_TO_   │
     └────┬───┘                    │CUSTOMER        │
          │ loading_complete       └────────────────┘
          └────────────────────────►

         ┌──────────────┐
    ┌───►ERROR_RECOVERY│
    │    └──────┬───────┘
    │           │ recovery_success
    │           └──────────────────────►WAITING
    │
    │    ┌───────────────┐
    └────┤EMERGENCY_STOP │ (требует ручного вмешательства)
         └───────────────┘
```

### Класс StateMachine

**Основные методы:**
```python
class StateMachine:
    def __init__(self, navigation, audio, order_verifier, 
                 serial_comm, lidar, box_controller):
        """Инициализация с ссылками на все подсистемы"""
    
    def start(self) -> None:
        """Запуск машины состояний"""
    
    def stop(self) -> None:
        """Остановка машины состояний"""
    
    def update(self) -> None:
        """
        Обновление текущего состояния
        Вызывается в главном цикле с частотой 10 Гц
        """
    
    def transition_to(self, new_state: State) -> None:
        """Переход в новое состояние"""
    
    def handle_error(self, error: Exception) -> None:
        """Обработка ошибок"""
```

**Обработчики состояний:**
- `update_waiting_state()` - Мониторинг LiDAR для обнаружения клиента
- `update_approaching_state()` - Отслеживание и подход к клиенту
- `update_verifying_state()` - Сканирование и проверка QR кода
- `update_navigating_to_warehouse_state()` - Навигация к складу
- `update_loading_state()` - Ожидание загрузки посылки
- `update_returning_to_customer_state()` - Возврат к клиенту
- `update_delivering_state()` - Доставка посылки
- `update_resetting_state()` - Возврат домой
- `update_error_recovery_state()` - Восстановление после ошибки
- `update_emergency_stop_state()` - Экстренная остановка

### Контекст состояния

```python
@dataclass
class StateContext:
    current_position: Position      # Текущая позиция робота
    target_position: Optional[Position]   # Целевая позиция
    customer_position: Optional[Position] # Сохраненная позиция клиента
    current_order_id: Optional[int]       # ID текущего заказа
    error_message: Optional[str]          # Сообщение об ошибке
```


### Обработка ошибок

**Типы ошибок:**

1. **Критические ошибки** (→ EMERGENCY_STOP):
   - LocalizationFailureError - Потеря локализации
   - SerialCommunicationError - Потеря связи с Arduino

2. **Некритические ошибки** (→ ERROR_RECOVERY):
   - PathPlanningFailureError - Не удалось построить путь
   - GoalUnreachableError - Цель недостижима
   - ObstacleCollisionError - Столкновение с препятствием
   - TimeoutError - Таймаут состояния

**Механизм восстановления:**
1. Остановка всех движений
2. Закрытие коробки если открыта
3. Воспроизведение звука ошибки
4. Попытка навигации домой
5. При успехе → WAITING
6. При неудаче → повторная попытка (макс 3)
7. После 3 неудач → EMERGENCY_STOP

---

## Система навигации

### Локализация (Particle Filter)

**Алгоритм:**

1. **Инициализация:**
   - Создание 200 частиц вокруг начальной позиции
   - Каждая частица: (x, y, theta, weight)

2. **Предсказание (Motion Model):**
   ```python
   # На основе одометрии
   for particle in particles:
       particle.x += delta_x + noise
       particle.y += delta_y + noise
       particle.theta += delta_theta + noise
   ```

3. **Обновление (Measurement Model):**
   ```python
   # На основе LiDAR сканирования
   for particle in particles:
       expected_scan = ray_cast(particle, map)
       actual_scan = lidar.get_scan()
       particle.weight = compute_likelihood(expected_scan, actual_scan)
   ```

4. **Ресемплинг:**
   ```python
   # Когда эффективное количество частиц < порога
   if effective_particles < threshold:
       particles = resample(particles, weights)
   ```

5. **Оценка позиции:**
   ```python
   # Взвешенное среднее всех частиц
   x = sum(p.x * p.weight for p in particles)
   y = sum(p.y * p.weight for p in particles)
   theta = circular_mean(p.theta * p.weight for p in particles)
   ```

### Планирование пути (A*)

**Алгоритм:**

1. **Дискретизация:**
   - Карта разбивается на сетку (разрешение 5 см)
   - Препятствия расширяются на OBSTACLE_CLEARANCE (30 см)

2. **Поиск пути:**
   ```python
   def a_star(start, goal, grid):
       open_set = PriorityQueue()
       open_set.put((0, start))
       came_from = {}
       g_score = {start: 0}
       
       while not open_set.empty():
           current = open_set.get()[1]
           
           if current == goal:
               return reconstruct_path(came_from, current)
           
           for neighbor in get_neighbors(current):
               if grid[neighbor] == OCCUPIED:
                   continue
               
               tentative_g = g_score[current] + distance(current, neighbor)
               
               if tentative_g < g_score.get(neighbor, inf):
                   came_from[neighbor] = current
                   g_score[neighbor] = tentative_g
                   f_score = tentative_g + heuristic(neighbor, goal)
                   open_set.put((f_score, neighbor))
       
       return None  # Путь не найден
   ```

3. **Генерация waypoints:**
   - Путь упрощается (удаление избыточных точек)
   - Waypoints создаются каждые 0.5 м


### Управление (PID Controller)

**Алгоритм:**

```python
class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp = kp  # Пропорциональный коэффициент
        self.ki = ki  # Интегральный коэффициент
        self.kd = kd  # Дифференциальный коэффициент
        self.integral = 0
        self.prev_error = 0
    
    def update(self, error, dt):
        # Пропорциональная составляющая
        p_term = self.kp * error
        
        # Интегральная составляющая
        self.integral += error * dt
        i_term = self.ki * self.integral
        
        # Дифференциальная составляющая
        derivative = (error - self.prev_error) / dt
        d_term = self.kd * derivative
        
        self.prev_error = error
        
        return p_term + i_term + d_term
```

**Применение:**
- **Линейный PID:** Управление скоростью движения к waypoint
- **Угловой PID:** Управление поворотом к waypoint

**Настройка коэффициентов:**
```python
# В config.py
PID_LINEAR_KP = 1.0   # Увеличить для более агрессивного движения
PID_LINEAR_KI = 0.0   # Обычно 0 для избежания накопления ошибки
PID_LINEAR_KD = 0.1   # Демпфирование колебаний

PID_ANGULAR_KP = 2.0  # Выше чем линейный для быстрых поворотов
PID_ANGULAR_KI = 0.0
PID_ANGULAR_KD = 0.2
```

---

## Тестирование

### Структура тестов

```
tests/
├── conftest.py           # Фикстуры pytest
├── unit/                 # Модульные тесты
│   ├── test_audio_system.py
│   ├── test_box_controller.py
│   ├── test_config.py
│   ├── test_navigation.py
│   ├── test_odometry.py
│   ├── test_order_verification.py
│   └── test_state_machine.py
├── property/             # Property-based тесты (опционально)
└── integration/          # Интеграционные тесты
```

### Запуск тестов

```bash
# Все модульные тесты
python -m pytest tests/unit/ -v

# Конкретный модуль
python -m pytest tests/unit/test_navigation.py -v

# С покрытием кода
python -m pytest tests/unit/ --cov=. --cov-report=html

# Тесты производительности
python test_performance.py
```

### Написание тестов

**Пример модульного теста:**
```python
import pytest
from navigation import NavigationSystem

def test_navigation_initialization(mock_lidar, mock_odometry, mock_serial):
    """Тест инициализации системы навигации"""
    nav = NavigationSystem(
        map_file='assets/maps/warehouse_map.yaml',
        lidar_interface=mock_lidar,
        odometry=mock_odometry,
        serial_comm=mock_serial
    )
    
    assert nav is not None
    assert nav.get_current_position() == (0.0, 0.0, 0.0)

def test_navigation_to_goal(mock_lidar, mock_odometry, mock_serial):
    """Тест навигации к цели"""
    nav = NavigationSystem(...)
    
    # Навигация к точке (1.0, 1.0)
    result = nav.navigate_to(1.0, 1.0)
    
    assert result == True
    x, y, theta = nav.get_current_position()
    assert abs(x - 1.0) < 0.1  # Допуск 10 см
    assert abs(y - 1.0) < 0.1
```


**Использование фикстур:**
```python
# В conftest.py
@pytest.fixture
def mock_serial():
    """Мок последовательной связи"""
    class MockSerial:
        def send_motor_command(self, *args):
            pass
        def send_servo_command(self, angle):
            pass
        def send_led_command(self, cmd):
            pass
    return MockSerial()

@pytest.fixture
def mock_lidar():
    """Мок LiDAR интерфейса"""
    class MockLiDAR:
        def get_scan(self):
            return []
        def detect_person(self):
            return None
    return MockLiDAR()
```

### Тестирование без оборудования

Все модули поддерживают работу с моками для тестирования без физического оборудования:

```python
# Мок Arduino
class MockArduino:
    def write(self, data):
        print(f"Mock Arduino: {data}")
    
    def readline(self):
        return b"ACK\n"

# Мок LiDAR
class MockLiDAR:
    def get_scan(self):
        # Возврат тестовых данных
        return [ScanPoint(1.0, 0.0, 100) for _ in range(360)]
```

---

## Расширение функциональности

### Добавление нового состояния

1. **Добавить в enum State:**
```python
class State(Enum):
    # ... существующие состояния
    NEW_STATE = "NEW_STATE"
```

2. **Создать обработчик:**
```python
def update_new_state(self) -> None:
    """
    Обновление состояния NEW_STATE
    
    Описание логики состояния
    """
    # Логика состояния
    pass
```

3. **Добавить в update():**
```python
def update(self) -> None:
    # ...
    elif self.current_state == State.NEW_STATE:
        self.update_new_state()
```

4. **Добавить переходы:**
```python
# В других состояниях
if condition:
    self.transition_to(State.NEW_STATE)
```

### Добавление нового сенсора

1. **Создать интерфейс:**
```python
# new_sensor.py
class NewSensorInterface:
    def __init__(self, port: str):
        """Инициализация сенсора"""
        self.port = port
        # Подключение к сенсору
    
    def read_data(self):
        """Чтение данных сенсора"""
        # Реализация чтения
        pass
    
    def close(self):
        """Закрытие соединения"""
        pass
```

2. **Добавить в main.py:**
```python
# Инициализация нового сенсора
new_sensor = NewSensorInterface(port='/dev/ttyUSB2')

# Передать в StateMachine
state_machine = StateMachine(
    # ... существующие параметры
    new_sensor=new_sensor
)
```

3. **Использовать в состояниях:**
```python
def update_some_state(self) -> None:
    data = self.new_sensor.read_data()
    # Обработка данных
```


### Добавление новой команды Arduino

1. **Расширить serialConnection.py:**
```python
def send_new_command(param1, param2):
    """
    Отправка новой команды Arduino
    
    Args:
        param1: Первый параметр
        param2: Второй параметр
    """
    command = f"NEW_CMD:{param1},{param2}\n"
    ser.write(command.encode())
    logger.info(f"Отправлена команда: {command.strip()}")
```

2. **Обновить Arduino код:**
```cpp
// В ideal_program.ino
void parseCommand(String command) {
    // ... существующие команды
    
    if (command.startsWith("NEW_CMD:")) {
        parseNewCommand(command.substring(8));
    }
}

void parseNewCommand(String params) {
    int commaIndex = params.indexOf(',');
    int param1 = params.substring(0, commaIndex).toInt();
    int param2 = params.substring(commaIndex + 1).toInt();
    
    // Выполнение команды
    executeNewCommand(param1, param2);
    
    // Отправка подтверждения
    Serial.println("ACK");
}
```

### Оптимизация производительности

**Профилирование:**
```python
import cProfile
import pstats

# Профилирование функции
profiler = cProfile.Profile()
profiler.enable()

# Код для профилирования
state_machine.update()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Топ 20 функций
```

**Оптимизация локализации:**
- Уменьшить количество частиц (100 вместо 200)
- Увеличить порог ресемплинга
- Использовать адаптивное количество частиц

**Оптимизация планирования:**
- Увеличить разрешение сетки (10 см вместо 5 см)
- Кэшировать статические препятствия
- Использовать инкрементальное планирование (D* Lite)

### Отладка

**Включение DEBUG логирования:**
```python
# В config.py
LOG_LEVEL = 'DEBUG'
```

**Визуализация навигации:**
```python
# Добавить в navigation.py
def visualize_particles(self):
    """Визуализация частиц для отладки"""
    import matplotlib.pyplot as plt
    
    x = [p.x for p in self.particles]
    y = [p.y for p in self.particles]
    weights = [p.weight for p in self.particles]
    
    plt.scatter(x, y, c=weights, cmap='hot')
    plt.colorbar(label='Weight')
    plt.xlabel('X (m)')
    plt.ylabel('Y (m)')
    plt.title('Particle Filter Visualization')
    plt.show()
```

**Запись траектории:**
```python
# Добавить в navigation.py
self.trajectory = []

def update_localization(self):
    # ... существующий код
    
    # Запись позиции
    x, y, theta = self.get_current_position()
    self.trajectory.append((x, y, theta, time.time()))

def save_trajectory(self, filename='trajectory.csv'):
    """Сохранение траектории для анализа"""
    import csv
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['x', 'y', 'theta', 'timestamp'])
        writer.writerows(self.trajectory)
```

---

## Лучшие практики

### Код

1. **Используйте type hints:**
```python
def navigate_to(self, target_x: float, target_y: float) -> bool:
    pass
```

2. **Документируйте функции на русском:**
```python
def update_localization(self) -> None:
    """
    Обновление локализации с использованием фильтра частиц
    
    Интегрирует данные одометрии и LiDAR для оценки позиции робота.
    Вызывается в главном цикле с частотой 10 Гц.
    """
```

3. **Обрабатывайте ошибки:**
```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Ошибка операции: {e}")
    handle_error(e)
```

4. **Используйте константы из config.py:**
```python
# Плохо
if distance < 0.3:
    pass

# Хорошо
if distance < config.OBSTACLE_CLEARANCE:
    pass
```

### Тестирование

1. **Тестируйте граничные случаи:**
```python
def test_navigation_zero_distance():
    """Тест навигации к текущей позиции"""
    nav = NavigationSystem(...)
    result = nav.navigate_to(0.0, 0.0)
    assert result == True
```

2. **Используйте моки для изоляции:**
```python
@patch('serialConnection.ser')
def test_with_mock_serial(mock_ser):
    # Тест без реального Arduino
    pass
```

3. **Проверяйте производительность:**
```python
def test_localization_rate():
    """Локализация должна работать >= 10 Гц"""
    start = time.time()
    for _ in range(100):
        nav.update_localization()
    duration = time.time() - start
    rate = 100 / duration
    assert rate >= 10.0
```

### Развертывание

1. **Используйте виртуальное окружение:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Создавайте резервные копии:**
```bash
./backup.sh
```

3. **Мониторьте логи:**
```bash
tail -f relaybot.log | grep ERROR
```

4. **Используйте systemd для автозапуска:**
```bash
sudo systemctl enable relaybot
```

---

## Справочная информация

### Системные требования

- **ОС:** Raspberry Pi OS (Debian-based)
- **Python:** 3.7+
- **RAM:** Минимум 2GB, рекомендуется 4GB
- **Диск:** Минимум 2GB свободного места

### Зависимости

См. `requirements.txt`:
- numpy - Математические операции
- scipy - Научные вычисления
- opencv-python - Обработка изображений
- pyzbar - Декодирование QR кодов
- pyserial - Последовательная связь
- playsound3 - Воспроизведение аудио
- pyyaml - Парсинг YAML
- sqlalchemy - ORM для базы данных
- pytest - Тестирование

### Полезные ссылки

- **LiDAR D500 документация:** https://www.ldrobot.com/
- **Raspberry Pi GPIO:** https://pinout.xyz/
- **Arduino Serial:** https://www.arduino.cc/reference/en/language/functions/communication/serial/
- **Particle Filter:** https://en.wikipedia.org/wiki/Particle_filter
- **A* Algorithm:** https://en.wikipedia.org/wiki/A*_search_algorithm

---

**Версия документа:** 1.0  
**Последнее обновление:** 09.02.2026  
**Автор:** RelayBot Development Team
