#!/bin/bash
# Скрипт быстрого запуска веб-интерфейса RelayBot

echo "=========================================="
echo "Запуск веб-интерфейса RelayBot"
echo "=========================================="

# Активация виртуального окружения
if [ -d "venv" ]; then
    echo "Активация виртуального окружения..."
    source venv/bin/activate
else
    echo "⚠ Виртуальное окружение не найдено (venv)"
    echo "Создайте его командой: python3 -m venv venv"
    exit 1
fi

# Проверка зависимостей
echo ""
echo "Проверка зависимостей..."
python test_web_setup.py

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Запуск веб-сервера..."
    echo "=========================================="
    python run_web_interface.py
else
    echo ""
    echo "✗ Проверка не пройдена. Установите зависимости:"
    echo "  pip install -r requirements.txt"
    exit 1
fi
