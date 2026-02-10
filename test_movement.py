#!/usr/bin/env python3
"""
Тест базового движения робота
"""
import time
import serialConnection
import config

print("=" * 60)
print("Тест движения робота")
print("=" * 60)

# Подключение
print(f"\nПодключение к Arduino: {config.ARDUINO_PORT}")
serialConnection.init_serial(config.ARDUINO_PORT, config.ARDUINO_BAUDRATE)
time.sleep(2)

print("\n1. Тест движения вперед (5 секунд)")
print("   Команда: left=100, right=100, dir=1,1")
serialConnection.send_motor_command(100, 100, 1, 1)
time.sleep(5)

print("\n2. Остановка")
print("   Команда: left=0, right=0")
serialConnection.send_motor_command(0, 0, 1, 1)
time.sleep(2)

print("\n3. Тест поворота влево (3 секунды)")
print("   Команда: left=80 назад, right=80 вперед")
serialConnection.send_motor_command(80, 80, 0, 1)
time.sleep(3)

print("\n4. Остановка")
serialConnection.send_motor_command(0, 0, 1, 1)
time.sleep(2)

print("\n5. Тест поворота вправо (3 секунды)")
print("   Команда: left=80 вперед, right=80 назад")
serialConnection.send_motor_command(80, 80, 1, 0)
time.sleep(3)

print("\n6. Остановка")
serialConnection.send_motor_command(0, 0, 1, 1)
time.sleep(1)

print("\n7. Тест движения назад (3 секунды)")
print("   Команда: left=100, right=100, dir=0,0")
serialConnection.send_motor_command(100, 100, 0, 0)
time.sleep(3)

print("\n8. Финальная остановка")
serialConnection.send_motor_command(0, 0, 1, 1)

print("\n" + "=" * 60)
print("Тест завершен")
print("=" * 60)

if serialConnection.ser:
    serialConnection.ser.close()

