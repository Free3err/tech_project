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
serialConnection.connect()
time.sleep(2)

# Параметры
SPEED = 100
TURN_SPEED = 80

print("\nТест 1: Движение вперед 2 метра (примерно 10 секунд)")
print(f"Команда: MOVE:{SPEED},{SPEED}")
serialConnection.ser.write(f"MOVE:{SPEED},{SPEED}\n".encode())
time.sleep(10)

print("\nОстановка")
serialConnection.ser.write(b"MOVE:0,0\n")
time.sleep(2)

print("\nТест 2: Поворот на 90 градусов влево (примерно 2 секунды)")
print(f"Команда: MOVE:-{TURN_SPEED},{TURN_SPEED}")
serialConnection.ser.write(f"MOVE:-{TURN_SPEED},{TURN_SPEED}\n".encode())
time.sleep(2)

print("\nОстановка")
serialConnection.ser.write(b"MOVE:0,0\n")
time.sleep(2)

print("\nТест 3: Движение вперед 1 метр (примерно 5 секунд)")
serialConnection.ser.write(f"MOVE:{SPEED},{SPEED}\n".encode())
time.sleep(5)

print("\nФинальная остановка")
serialConnection.ser.write(b"MOVE:0,0\n")

print("\n" + "=" * 60)
print("Тест завершен")
print("Робот должен был проехать букву 'Г'")
print("=" * 60)

serialConnection.disconnect()
