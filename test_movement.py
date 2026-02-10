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
serialConnection.connect()
time.sleep(2)

print("\n1. Тест движения вперед (5 секунд)")
print("   Команда: MOVE:100,100")
serialConnection.ser.write(b"MOVE:100,100\n")
time.sleep(5)

print("\n2. Остановка")
print("   Команда: MOVE:0,0")
serialConnection.ser.write(b"MOVE:0,0\n")
time.sleep(2)

print("\n3. Тест поворота влево (3 секунды)")
print("   Команда: MOVE:-80,80")
serialConnection.ser.write(b"MOVE:-80,80\n")
time.sleep(3)

print("\n4. Остановка")
serialConnection.ser.write(b"MOVE:0,0\n")
time.sleep(2)

print("\n5. Тест поворота вправо (3 секунды)")
print("   Команда: MOVE:80,-80")
serialConnection.ser.write(b"MOVE:80,-80\n")
time.sleep(3)

print("\n6. Остановка")
serialConnection.ser.write(b"MOVE:0,0\n")
time.sleep(1)

print("\n7. Тест движения назад (3 секунды)")
print("   Команда: MOVE:-100,-100")
serialConnection.ser.write(b"MOVE:-100,-100\n")
time.sleep(3)

print("\n8. Финальная остановка")
serialConnection.ser.write(b"MOVE:0,0\n")

print("\n" + "=" * 60)
print("Тест завершен")
print("=" * 60)

serialConnection.disconnect()
