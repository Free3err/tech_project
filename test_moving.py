#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки движения моторов и серво
Позволяет вручную управлять роботом и тестировать команды
"""

import time
import sys
import serialConnection


def print_menu():
    """Вывод меню команд"""
    print("\n" + "="*50)
    print("ТЕСТ ДВИЖЕНИЯ И СЕРВО")
    print("="*50)
    print("Моторы:")
    print("  w - Вперед (dir=1,1)")
    print("  s - Назад (dir=0,0)")
    print("  a - Поворот влево")
    print("  d - Поворот вправо")
    print("  x - Стоп")
    print("\nСерво:")
    print("  1 - Угол 112°")
    print("  2 - Угол 35°")
    print("  3 - Угол 58°")
    print("\nДругое:")
    print("  q - Выход")
    print("="*50)


def send_motor_command(speed_left, speed_right, dir_left, dir_right):
    """Отправка команды моторам"""
    try:
        command = f"M{speed_left},{speed_right},{dir_left},{dir_right}\n"
        serialConnection.ser.write(command.encode())
        print(f"→ Моторы: {command.strip()}")
        time.sleep(0.1)
    except Exception as e:
        print(f"✗ Ошибка отправки команды моторам: {e}")


def send_servo_command(angle):
    """Отправка команды серво"""
    try:
        command = f"S{angle}\n"
        serialConnection.ser.write(command.encode())
        print(f"→ Серво: {angle}°")
        time.sleep(0.1)
    except Exception as e:
        print(f"✗ Ошибка отправки команды серво: {e}")


def stop_motors():
    """Остановка моторов"""
    send_motor_command(0, 0, 0, 0)


def main():
    """Главная функция"""
    print("Инициализация последовательного соединения...")
    
    try:
        serialConnection.init_serial(port='/dev/ttyACM0', baudrate=9600)
        print("✓ Соединение установлено")
    except Exception as e:
        print(f"✗ Ошибка подключения: {e}")
        return 1
    
    # Ожидание инициализации Arduino
    print("Ожидание инициализации Arduino...")
    time.sleep(2)
    
    print_menu()
    
    try:
        while True:
            # Чтение команды
            cmd = input("\nВведите команду: ").strip().lower()
            
            if cmd == 'q':
                print("Выход...")
                break
            
            elif cmd == 'w':
                # Вперед
                send_motor_command(140, 140, 1, 1)
                
            elif cmd == 's':
                # Назад
                send_motor_command(140, 140, 0, 0)
                
            elif cmd == 'a':
                # Поворот влево
                send_motor_command(100, 100, 0, 1)
                
            elif cmd == 'd':
                # Поворот вправо
                send_motor_command(100, 100, 1, 0)
                
            elif cmd == 'x':
                # Стоп
                stop_motors()
                
            elif cmd == '1':
                # Серво 112°
                send_servo_command(112)
                
            elif cmd == '2':
                # Серво 35°
                send_servo_command(35)
                
            elif cmd == '3':
                # Серво 58°
                send_servo_command(58)
                
            else:
                print("Неизвестная команда")
                print_menu()
    
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    
    finally:
        # Остановка моторов перед выходом
        print("\nОстановка моторов...")
        stop_motors()
        
        # Закрытие соединения
        if serialConnection.ser and serialConnection.ser.is_open:
            serialConnection.ser.close()
            print("✓ Соединение закрыто")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
