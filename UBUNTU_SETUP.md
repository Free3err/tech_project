# RelayBot - Установка на Ubuntu 22.04

**Версия:** Ubuntu 22.04 LTS  
**Python:** 3.10+  
**Дата:** 09.02.2026

---

## Системные требования

- Ubuntu 22.04 LTS (или новее)
- Python 3.10 или выше
- 2GB RAM минимум (4GB рекомендуется)
- 2GB свободного места на диске
- USB порты для Arduino и LiDAR
- USB камера или Raspberry Pi Camera

---

## Быстрая установка

### 1. Обновление системы

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Установка системных зависимостей

```bash
# Python и основные инструменты
sudo apt install -y python3 python3-pip python3-venv git

# Библиотеки для аудио
sudo apt install -y portaudio19-dev ffmpeg

# Библиотеки для компьютерного зрения
sudo apt install -y python3-opencv libopencv-dev

# Библиотеки для QR кодов
sudo apt install -y libzbar0 zbar-tools

# Дополнительные библиотеки
sudo apt install -y build-essential libssl-dev libffi-dev
```

### 3. Автоматическая установка RelayBot

```bash
# Клонирование репозитория
git clone <repository_url>
cd relaybot

# Запуск установки
chmod +x install.sh
sudo ./install.sh

# Перезагрузка для применения прав доступа
sudo reboot
```

---

## Ручная установка (если автоматическая не работает)

### 1. Создание виртуального окружения

```bash
cd /path/to/relaybot
python3 -m venv venv
source venv/bin/activate
```

### 2. Установка Python пакетов

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Настройка прав доступа к портам

```bash
# Добавление пользователя в группы
sudo usermod -a -G dialout $USER
sudo usermod -a -G video $USER
sudo usermod -a -G tty $USER

# Применение изменений (требуется перезагрузка)
sudo reboot
```

### 4. Проверка установки

```bash
# Проверка Python
python3 --version  # Должно быть >= 3.10

# Проверка портов
ls /dev/tty{ACM,USB}*  # Arduino и LiDAR
ls /dev/video*         # Камера

# Проверка OpenCV
python3 -c "import cv2; print(cv2.__version__)"

# Проверка pyzbar
python3 -c "import pyzbar; print('pyzbar OK')"

# Проверка pyserial
python3 -c "import serial; print('pyserial OK')"
```

---

## Настройка портов

### Определение портов устройств

```bash
# Просмотр всех последовательных портов
ls -l /dev/tty{ACM,USB}*

# Мониторинг подключения устройств
dmesg | grep tty

# Или используйте
sudo dmesg -w
# Затем подключите устройство и посмотрите какой порт появился
```

### Типичные порты на Ubuntu

- **Arduino:** `/dev/ttyACM0` или `/dev/ttyUSB0`
- **LiDAR:** `/dev/ttyUSB0` или `/dev/ttyUSB1`
- **Камера:** `/dev/video0`

### Постоянные имена портов (опционально)

Создайте udev правила для постоянных имен:

```bash
# Узнайте ID устройства
udevadm info -a -n /dev/ttyACM0 | grep '{idVendor}\|{idProduct}'

# Создайте правило
sudo nano /etc/udev/rules.d/99-relaybot.rules
```

Добавьте:
```
# Arduino
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0043", SYMLINK+="arduino"

# LiDAR
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="lidar"
```

Перезагрузите правила:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Теперь можно использовать `/dev/arduino` и `/dev/lidar` в config.py

---

## Настройка systemd сервиса

Сервис создается автоматически при установке. Управление:

```bash
# Запуск
sudo systemctl start relaybot

# Остановка
sudo systemctl stop relaybot

# Перезапуск
sudo systemctl restart relaybot

# Статус
sudo systemctl status relaybot

# Автозапуск при загрузке
sudo systemctl enable relaybot

# Отключение автозапуска
sudo systemctl disable relaybot

# Просмотр логов
sudo journalctl -u relaybot -f
```

---

## Решение проблем Ubuntu

### Ошибка: "Permission denied" для портов

```bash
# Проверьте группы пользователя
groups $USER

# Должны быть: dialout, tty, video

# Если нет, добавьте:
sudo usermod -a -G dialout $USER
sudo usermod -a -G tty $USER
sudo usermod -a -G video $USER

# Перезагрузите систему
sudo reboot
```

### Ошибка: "No module named 'cv2'"

```bash
# Установите OpenCV
sudo apt install python3-opencv

# Или через pip в виртуальном окружении
pip install opencv-python
```

### Ошибка: "pyzbar not found"

```bash
# Установите системную библиотеку
sudo apt install libzbar0

# Переустановите pyzbar
pip uninstall pyzbar
pip install pyzbar
```

### Ошибка: "Could not open audio device"

```bash
# Установите portaudio
sudo apt install portaudio19-dev

# Переустановите pyaudio (если используется)
pip uninstall pyaudio
pip install pyaudio

# Проверьте аудио устройства
aplay -l
```

### Ошибка: "Camera not found"

```bash
# Проверьте камеру
ls /dev/video*

# Проверьте права
sudo chmod 666 /dev/video0

# Тест камеры
ffplay /dev/video0

# Или
cheese  # GUI приложение для камеры
```

### LiDAR не подключается

```bash
# Проверьте порт
ls -l /dev/ttyUSB*

# Проверьте права
sudo chmod 666 /dev/ttyUSB0

# Проверьте скорость
stty -F /dev/ttyUSB0 230400

# Тест чтения
cat /dev/ttyUSB0
```

---

## Оптимизация для Raspberry Pi

Если используете Raspberry Pi с Ubuntu:

### 1. Увеличение swap (для 2GB RAM)

```bash
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Установите CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### 2. Отключение GUI (для экономии ресурсов)

```bash
# Загрузка в консольный режим
sudo systemctl set-default multi-user.target

# Возврат к GUI
sudo systemctl set-default graphical.target
```

### 3. Оптимизация производительности

```bash
# Разгон (осторожно!)
sudo nano /boot/firmware/config.txt
# Добавьте:
# over_voltage=2
# arm_freq=1750

# Перезагрузка
sudo reboot
```

### 4. Мониторинг температуры

```bash
# Температура CPU
vcgencmd measure_temp

# Мониторинг в реальном времени
watch -n 1 vcgencmd measure_temp
```

---

## Автозапуск при загрузке

### Через systemd (рекомендуется)

```bash
# Включение автозапуска
sudo systemctl enable relaybot

# Проверка
sudo systemctl is-enabled relaybot
```

### Через cron (альтернатива)

```bash
crontab -e
# Добавьте:
@reboot sleep 30 && cd /path/to/relaybot && /path/to/relaybot/venv/bin/python3 main.py
```

---

## Мониторинг и отладка

### Просмотр логов

```bash
# Логи systemd
sudo journalctl -u relaybot -f

# Логи приложения
tail -f /path/to/relaybot/relaybot.log

# Все логи
tail -f /path/to/relaybot/*.log
```

### Мониторинг ресурсов

```bash
# CPU и память
htop

# Процессы Python
ps aux | grep python

# Использование диска
df -h

# Температура (Raspberry Pi)
vcgencmd measure_temp
```

### Отладка

```bash
# Запуск в режиме отладки
cd /path/to/relaybot
source venv/bin/activate
python3 main.py

# С подробными логами
LOG_LEVEL=DEBUG python3 main.py
```

---

## Резервное копирование

```bash
# Создание резервной копии
./backup.sh

# Восстановление
./backup.sh restore backups/relaybot_backup_2026-02-09.tar.gz

# Автоматическое резервное копирование (cron)
crontab -e
# Добавьте (каждый день в 2:00):
0 2 * * * cd /path/to/relaybot && ./backup.sh
```

---

## Обновление системы

```bash
# Обновление Ubuntu
sudo apt update
sudo apt upgrade -y

# Обновление Python пакетов
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Перезапуск сервиса
sudo systemctl restart relaybot
```

---

## Полезные команды

```bash
# Проверка версий
python3 --version
pip --version
git --version

# Информация о системе
uname -a
lsb_release -a

# Свободное место
df -h

# Память
free -h

# USB устройства
lsusb

# Последовательные порты
dmesg | grep tty

# Сетевые интерфейсы
ip addr

# Процессы
ps aux | grep python
```

---

## Контрольный список установки

- [ ] Ubuntu 22.04 установлена и обновлена
- [ ] Системные зависимости установлены
- [ ] Python 3.10+ установлен
- [ ] Виртуальное окружение создано
- [ ] Python пакеты установлены
- [ ] Права доступа к портам настроены
- [ ] Arduino подключен и определяется
- [ ] LiDAR подключен и определяется
- [ ] Камера работает
- [ ] config.py настроен (порты, параметры робота)
- [ ] Карта окружения создана
- [ ] База данных инициализирована
- [ ] Аудио файлы сгенерированы
- [ ] Тесты проходят
- [ ] Systemd сервис работает
- [ ] Логи пишутся корректно

---

**Версия документа:** 1.0  
**Последнее обновление:** 09.02.2026  
**Платформа:** Ubuntu 22.04 LTS
