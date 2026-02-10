#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт запуска веб-интерфейса RelayBot
Запускает Flask сервер для управления роботом через браузер
"""

import sys
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

if __name__ == '__main__':
    from web_interface import run_web_interface
    
    # Запуск веб-интерфейса
    # По умолчанию доступен на http://0.0.0.0:5000
    # Можно открыть в браузере: http://localhost:5000 или http://<IP_адрес_робота>:5000
    run_web_interface(host='0.0.0.0', port=5000)
