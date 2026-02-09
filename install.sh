#!/bin/bash
# RelayBot Installation Script
# Автоматическая установка и настройка системы

set -e  # Выход при ошибке

echo "========================================="
echo "RelayBot Installation Script"
echo "========================================="
echo ""

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo "Пожалуйста, запустите скрипт с правами root (sudo ./install.sh)"
    exit 1
fi

# Получение имени пользователя (не root)
REAL_USER=${SUDO_USER:-$USER}
INSTALL_DIR=$(pwd)

echo "Установка для пользователя: $REAL_USER"
echo "Директория установки: $INSTALL_DIR"
echo ""

# Обновление системы
echo "[1/10] Обновление системы..."
apt update
apt upgrade -y

# Установка системных зависимостей
echo "[2/10] Установка системных зависимостей..."
apt install -y python3 python3-pip python3-venv
apt install -y portaudio19-dev python3-opencv
apt install -y git

# Создание виртуального окружения
echo "[3/10] Создание виртуального окружения..."
if [ ! -d "venv" ]; then
    sudo -u $REAL_USER python3 -m venv venv
fi

# Активация виртуального окружения и установка Python пакетов
echo "[4/10] Установка Python зависимостей..."
sudo -u $REAL_USER bash -c "source venv/bin/activate && pip install --upgrade pip"
sudo -u $REAL_USER bash -c "source venv/bin/activate && pip install -r requirements.txt"

# Создание необходимых директорий
echo "[5/10] Создание директорий..."
sudo -u $REAL_USER mkdir -p assets/audio
sudo -u $REAL_USER mkdir -p assets/maps
sudo -u $REAL_USER mkdir -p backups
sudo -u $REAL_USER mkdir -p docs

# Настройка прав доступа к портам
echo "[6/10] Настройка прав доступа к портам..."
usermod -a -G dialout $REAL_USER
usermod -a -G tty $REAL_USER

# Инициализация базы данных
echo "[7/10] Инициализация базы данных..."
if [ ! -f "assets/orders.db" ]; then
    sudo -u $REAL_USER bash -c "source venv/bin/activate && python3 -c 'from db.db import init_db; init_db()'"
    echo "База данных создана"
else
    echo "База данных уже существует"
fi


# Создание systemd сервиса
echo "[8/10] Создание systemd сервиса..."
cat > /etc/systemd/system/relaybot.service << EOF
[Unit]
Description=RelayBot Autonomous Delivery System
After=network.target

[Service]
Type=simple
User=$REAL_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузка systemd
systemctl daemon-reload

# Проверка подключения оборудования
echo "[9/10] Проверка подключения оборудования..."
echo ""
echo "Доступные последовательные порты:"
ls -l /dev/tty{ACM,USB}* 2>/dev/null || echo "Последовательные порты не найдены"
echo ""
echo "Доступные видео устройства:"
ls -l /dev/video* 2>/dev/null || echo "Видео устройства не найдены"
echo ""

# Установка прав на скрипты
echo "[10/10] Установка прав на скрипты..."
chmod +x backup.sh
chown $REAL_USER:$REAL_USER backup.sh

echo ""
echo "========================================="
echo "Установка завершена!"
echo "========================================="
echo ""
echo "Следующие шаги:"
echo "1. Перезагрузите систему для применения прав доступа к портам:"
echo "   sudo reboot"
echo ""
echo "2. После перезагрузки отредактируйте config.py:"
echo "   - Установите правильные порты для Arduino и LiDAR"
echo "   - Настройте параметры робота (WHEEL_BASE, WHEEL_RADIUS)"
echo ""
echo "3. Создайте карту окружения в assets/maps/warehouse_map.yaml"
echo ""
echo "4. Сгенерируйте аудио файлы:"
echo "   python3 generate_audio_files.py"
echo ""
echo "5. Запустите систему:"
echo "   sudo systemctl start relaybot"
echo ""
echo "6. Проверьте статус:"
echo "   sudo systemctl status relaybot"
echo ""
echo "7. Просмотр логов:"
echo "   tail -f relaybot.log"
echo ""
echo "Для автозапуска при загрузке:"
echo "   sudo systemctl enable relaybot"
echo ""
echo "========================================="
