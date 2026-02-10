#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт проверки готовности веб-интерфейса
Проверяет наличие всех необходимых зависимостей и файлов
"""

import sys

def check_dependencies():
    """Проверка установленных зависимостей"""
    print("Проверка зависимостей...")
    
    dependencies = {
        'flask': 'Flask',
        'flask_socketio': 'flask-socketio',
        'cv2': 'opencv-python',
        'numpy': 'numpy'
    }
    
    missing = []
    for module, package in dependencies.items():
        try:
            __import__(module)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - НЕ УСТАНОВЛЕН")
            missing.append(package)
    
    return missing


def check_files():
    """Проверка наличия необходимых файлов"""
    print("\nПроверка файлов...")
    
    import os
    
    files = [
        'web_interface.py',
        'templates/index.html',
        'config.py',
        'serialConnection.py',
        'lidar_interface.py'
    ]
    
    missing = []
    for file in files:
        if os.path.exists(file):
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} - НЕ НАЙДЕН")
            missing.append(file)
    
    return missing


def check_config():
    """Проверка конфигурации"""
    print("\nПроверка конфигурации...")
    
    try:
        import config
        
        required_params = [
            'ARDUINO_PORT',
            'ARDUINO_BAUDRATE',
            'LIDAR_PORT',
            'LIDAR_BAUDRATE'
        ]
        
        for param in required_params:
            if hasattr(config, param):
                value = getattr(config, param)
                print(f"  ✓ {param} = {value}")
            else:
                print(f"  ✗ {param} - НЕ НАЙДЕН")
        
        return True
    except Exception as e:
        print(f"  ✗ Ошибка загрузки config.py: {e}")
        return False


def main():
    """Главная функция проверки"""
    print("=" * 60)
    print("ПРОВЕРКА ГОТОВНОСТИ ВЕБ-ИНТЕРФЕЙСА RELAYBOT")
    print("=" * 60)
    
    # Проверка зависимостей
    missing_deps = check_dependencies()
    
    # Проверка файлов
    missing_files = check_files()
    
    # Проверка конфигурации
    config_ok = check_config()
    
    # Итоги
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ПРОВЕРКИ")
    print("=" * 60)
    
    if not missing_deps and not missing_files and config_ok:
        print("✓ Все проверки пройдены!")
        print("\nДля запуска веб-интерфейса выполните:")
        print("  python run_web_interface.py")
        print("\nИнтерфейс будет доступен по адресу:")
        print("  http://localhost:5000")
        return 0
    else:
        print("✗ Обнаружены проблемы:")
        
        if missing_deps:
            print(f"\nОтсутствующие зависимости ({len(missing_deps)}):")
            for dep in missing_deps:
                print(f"  - {dep}")
            print("\nУстановите их командой:")
            print("  pip install " + " ".join(missing_deps))
        
        if missing_files:
            print(f"\nОтсутствующие файлы ({len(missing_files)}):")
            for file in missing_files:
                print(f"  - {file}")
        
        if not config_ok:
            print("\nПроблемы с конфигурацией")
        
        return 1


if __name__ == '__main__':
    sys.exit(main())
