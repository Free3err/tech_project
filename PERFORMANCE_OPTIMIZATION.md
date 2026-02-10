# Оптимизация производительности RelayBot

**Дата:** 10.02.2026  
**Проблема:** Цикл выполняется 10+ секунд вместо 0.1 секунды

---

## Выполненные оптимизации

### 1. Уменьшение количества частиц
```python
# config.py
NUM_PARTICLES = 50  # Было 150
```

### 2. Снижение частоты локализации
```python
# config.py
LOCALIZATION_UPDATE_RATE = 5  # Было 10 Гц
```

### 3. Пропуск обновлений локализации
```python
# state_machine.py
_localization_skip_rate = 2  # Обновлять каждую 2-ю итерацию
```

### 4. Уменьшение выборки лучей LiDAR
```python
# navigation.py
sample_size = min(len(scan), 12)  # Было 36
```

---

## Дополнительные оптимизации (если нужно)

### Опция 1: Отключить локализацию в WAITING
```python
# В state_machine.py, метод update()
# Обновлять локализацию только когда робот движется
if self.current_state in [State.APPROACHING, State.NAVIGATING_TO_WAREHOUSE, 
                          State.RETURNING_TO_CUSTOMER, State.RESETTING]:
    self.navigation.update_localization()
```

### Опция 2: Использовать только одометрию
```python
# В navigation.py, закомментировать фильтр частиц
def update_localization(self):
    # Использовать только одометрию без LiDAR
    x, y, theta = self.odometry.get_pose()
    self.estimated_position = Position(x, y, theta)
```

### Опция 3: Уменьшить разрешение карты
```python
# config.py
MAP_RESOLUTION = 0.05  # Было 0.02 (увеличить до 5см)
```

### Опция 4: Упростить ray casting
```python
# navigation.py
# Использовать упрощенный ray casting без интерполяции
```

---

## Тестирование производительности

```bash
cd ~/test_tech_project
source venv/bin/activate
python3 test_performance.py
```

Ожидаемые результаты после оптимизации:
- Локализация: 5-10 Гц (было требование ≥10 Гц, но для прототипа 5 Гц достаточно)
- Цикл обновления: <200 мс (цель <100 мс)

---

## Мониторинг производительности

```bash
# Запуск с профилированием
python3 -m cProfile -o profile.stats main.py

# Анализ результатов
python3 -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

---

## Если производительность всё ещё низкая

### Проверьте систему:

```bash
# CPU
top -p $(pgrep -f main.py)

# Температура (Raspberry Pi)
vcgencmd measure_temp

# Память
free -h
```

### Возможные причины:

1. **Перегрев** - добавьте охлаждение
2. **Swap активен** - увеличьте RAM или отключите фоновые процессы
3. **LiDAR медленный** - проверьте скорость порта (230400 baud)
4. **Камера захватывает ресурсы** - отключите когда не используется

---

## Режим минимальной производительности

Для очень слабых систем (Raspberry Pi Zero, старые модели):

```python
# config.py - Экстремальная оптимизация
NUM_PARTICLES = 20
LOCALIZATION_UPDATE_RATE = 2
MAP_RESOLUTION = 0.10
MAX_PLANNING_ITERATIONS = 1000

# state_machine.py
_localization_skip_rate = 5  # Обновлять каждую 5-ю итерацию

# navigation.py
sample_size = min(len(scan), 6)  # Только 6 лучей
```

---

**Версия документа:** 1.0  
**Последнее обновление:** 10.02.2026
