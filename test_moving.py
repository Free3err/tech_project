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
                print("→ Вперед")
                serialConnection.send_motor_command(140, 140, 1, 1)
                
            elif cmd == 's':
                # Назад
                print("→ Назад")
                serialConnection.send_motor_command(140, 140, 0, 0)
                
            elif cmd == 'a':
                # Поворот влево
                print("→ Поворот влево")
                serialConnection.send_motor_command(100, 100, 0, 1)
                
            elif cmd == 'd':
                # Поворот вправо
                print("→ Поворот вправо")
                serialConnection.send_motor_command(100, 100, 1, 0)
                
            elif cmd == 'x':
                # Стоп
                print("→ Стоп")
                serialConnection.send_motor_command(0, 0, 0, 0)
                
            elif cmd == '1':
                # Серво 112°
                print("→ Серво: 112°")
                serialConnection.send_servo_command(112)
                
            elif cmd == '2':
                # Серво 35°
                print("→ Серво: 35°")
                serialConnection.send_servo_command(35)
                
            elif cmd == '3':
                # Серво 58°
                print("→ Серво: 58°")
                serialConnection.send_servo_command(58)
                
            else:
                print("Неизвестная команда")
                print_menu()
    
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    
    finally:
        # Остановка моторов перед выходом
        print("\nОстановка моторов...")
        try:
            serialConnection.send_motor_command(0, 0, 0, 0)
        except:
            pass
        
        # Закрытие соединения
        if serialConnection.ser and serialConnection.ser.is_open:
            serialConnection.ser.close()
            print("✓ Соединение закрыто")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
