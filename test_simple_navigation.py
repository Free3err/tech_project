#!/usr/bin/env python3
"""
Простой тест навигации - движение по времени без одометрии
"""
import time
import serialConnection
import config

print("=" * 60)
print("Простой тест навигации (без одометрии)")
print("=" * 60)

# Подключение
print(f"\nПодключение к Arduino: {config.ARDUINO_PORT}")
serialConnection.init_serial(config.ARDUINO_PORT, config.ARDUINO_BAUDRATE)
time.sleep(2)

# Параметры
SPEED = 100
TURN_SPEED = 80

print("\nТест 1: Движение вперед 2 метра (примерно 10 секунд)")
print(f"Команда: left={SPEED}, right={SPEED}, dir=1,1")
serialConnection.send_motor_command(SPEED, SPEED, 1, 1)
time.sleep(10)

print("\nОстановка")
serialConnection.send_motor_command(0, 0, 1, 1)
time.sleep(2)

print("\nТест 2: Поворот на 90 градусов влево (примерно 2 секунды)")
print(f"Команда: left={TURN_SPEED} назад, right={TURN_SPEED} вперед")
serialConnection.send_motor_command(TURN_SPEED, TURN_SPEED, 0, 1)
time.sleep(2)

print("\nОстановка")
serialConnection.send_motor_command(0, 0, 1, 1)
time.sleep(2)

print("\nТест 3: Движение вперед 1 метр (примерно 5 секунд)")
serialConnection.send_motor_command(SPEED, SPEED, 1, 1)
time.sleep(5)

print("\nФинальная остановка")
serialConnection.send_motor_command(0, 0, 1, 1)

print("\n" + "=" * 60)
print("Тест завершен")
print("Робот должен был проехать букву 'Г'")
print("=" * 60)

if serialConnection.ser:
    serialConnection.ser.close()

