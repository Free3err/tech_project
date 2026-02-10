#!/bin/bash
# Запуск RelayBot в headless режиме (без GUI)

export HEADLESS=1
export QT_QPA_PLATFORM=offscreen

cd "$(dirname "$0")"
source venv/bin/activate
python3 main.py
