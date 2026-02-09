#!/bin/bash
# RelayBot Backup and Restore Script
# Создание и восстановление резервных копий системы

set -e

BACKUP_DIR="backups"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_NAME="relaybot_backup_$DATE.tar.gz"

# Функция создания резервной копии
backup() {
    echo "========================================="
    echo "RelayBot Backup Script"
    echo "========================================="
    echo ""
    
    # Создание директории для резервных копий
    mkdir -p $BACKUP_DIR
    
    echo "Создание резервной копии..."
    echo "Дата: $DATE"
    echo ""
    
    # Список файлов для резервного копирования
    FILES_TO_BACKUP=(
        "config.py"
        "assets/orders.db"
        "assets/maps/"
        "assets/audio/"
        "*.log"
        ".kiro/"
    )
    
    # Создание временной директории
    TEMP_DIR=$(mktemp -d)
    BACKUP_CONTENT="$TEMP_DIR/relaybot_backup"
    mkdir -p $BACKUP_CONTENT
    
    # Копирование файлов
    echo "Копирование файлов..."
    for item in "${FILES_TO_BACKUP[@]}"; do
        if [ -e "$item" ]; then
            echo "  - $item"
            cp -r "$item" "$BACKUP_CONTENT/" 2>/dev/null || true
        fi
    done
    
    # Создание информационного файла
    cat > "$BACKUP_CONTENT/backup_info.txt" << EOF
RelayBot Backup Information
===========================
Date: $DATE
Hostname: $(hostname)
User: $USER
Python Version: $(python3 --version)
Git Commit: $(git rev-parse HEAD 2>/dev/null || echo "N/A")
Git Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "N/A")
EOF
    
    # Создание архива
    echo ""
    echo "Создание архива..."
    cd $TEMP_DIR
    tar -czf "$BACKUP_NAME" relaybot_backup/
    cd - > /dev/null
    
    # Перемещение архива в директорию резервных копий
    mv "$TEMP_DIR/$BACKUP_NAME" "$BACKUP_DIR/"
    
    # Очистка временной директории
    rm -rf $TEMP_DIR
    
    # Информация о резервной копии
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME" | cut -f1)
    
    echo ""
    echo "========================================="
    echo "Резервная копия создана успешно!"
    echo "========================================="
    echo "Файл: $BACKUP_DIR/$BACKUP_NAME"
    echo "Размер: $BACKUP_SIZE"
    echo ""
    
    # Список всех резервных копий
    echo "Доступные резервные копии:"
    ls -lh $BACKUP_DIR/*.tar.gz 2>/dev/null || echo "Нет резервных копий"
    echo ""
    
    # Очистка старых резервных копий (оставляем последние 10)
    echo "Очистка старых резервных копий (оставляем последние 10)..."
    cd $BACKUP_DIR
    ls -t relaybot_backup_*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm
    cd - > /dev/null
    
    echo "Готово!"
}


# Функция восстановления из резервной копии
restore() {
    local BACKUP_FILE=$1
    
    echo "========================================="
    echo "RelayBot Restore Script"
    echo "========================================="
    echo ""
    
    # Проверка наличия файла резервной копии
    if [ -z "$BACKUP_FILE" ]; then
        echo "Ошибка: Не указан файл резервной копии"
        echo ""
        echo "Использование: $0 restore <backup_file>"
        echo ""
        echo "Доступные резервные копии:"
        ls -lh $BACKUP_DIR/*.tar.gz 2>/dev/null || echo "Нет резервных копий"
        exit 1
    fi
    
    if [ ! -f "$BACKUP_FILE" ]; then
        # Попробовать найти в директории резервных копий
        if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
            BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
        else
            echo "Ошибка: Файл резервной копии не найден: $BACKUP_FILE"
            exit 1
        fi
    fi
    
    echo "Восстановление из: $BACKUP_FILE"
    echo ""
    
    # Подтверждение
    read -p "Это действие перезапишет текущие файлы. Продолжить? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Восстановление отменено"
        exit 0
    fi
    
    # Создание резервной копии текущего состояния перед восстановлением
    echo ""
    echo "Создание резервной копии текущего состояния..."
    backup
    
    # Создание временной директории
    TEMP_DIR=$(mktemp -d)
    
    # Распаковка архива
    echo ""
    echo "Распаковка архива..."
    tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"
    
    # Восстановление файлов
    echo "Восстановление файлов..."
    
    # Остановка сервиса если запущен
    if systemctl is-active --quiet relaybot; then
        echo "Остановка сервиса relaybot..."
        sudo systemctl stop relaybot
        SERVICE_WAS_RUNNING=true
    else
        SERVICE_WAS_RUNNING=false
    fi
    
    # Копирование файлов
    cp -r "$TEMP_DIR/relaybot_backup/"* .
    
    # Очистка временной директории
    rm -rf $TEMP_DIR
    
    # Запуск сервиса если был запущен
    if [ "$SERVICE_WAS_RUNNING" = true ]; then
        echo "Запуск сервиса relaybot..."
        sudo systemctl start relaybot
    fi
    
    echo ""
    echo "========================================="
    echo "Восстановление завершено успешно!"
    echo "========================================="
    echo ""
    
    # Показать информацию о резервной копии
    if [ -f "backup_info.txt" ]; then
        echo "Информация о восстановленной резервной копии:"
        cat backup_info.txt
        echo ""
    fi
}

# Функция вывода справки
usage() {
    echo "RelayBot Backup and Restore Script"
    echo ""
    echo "Использование:"
    echo "  $0                    - Создать резервную копию"
    echo "  $0 backup             - Создать резервную копию"
    echo "  $0 restore <file>     - Восстановить из резервной копии"
    echo "  $0 list               - Показать список резервных копий"
    echo "  $0 help               - Показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  $0"
    echo "  $0 restore backups/relaybot_backup_2026-02-09_12-30-00.tar.gz"
    echo "  $0 restore relaybot_backup_2026-02-09_12-30-00.tar.gz"
    echo ""
}

# Функция вывода списка резервных копий
list_backups() {
    echo "========================================="
    echo "Доступные резервные копии"
    echo "========================================="
    echo ""
    
    if [ -d "$BACKUP_DIR" ] && [ "$(ls -A $BACKUP_DIR/*.tar.gz 2>/dev/null)" ]; then
        ls -lh $BACKUP_DIR/*.tar.gz
        echo ""
        echo "Всего резервных копий: $(ls $BACKUP_DIR/*.tar.gz 2>/dev/null | wc -l)"
    else
        echo "Резервные копии не найдены"
    fi
    echo ""
}

# Основная логика
case "${1:-backup}" in
    backup)
        backup
        ;;
    restore)
        restore "$2"
        ;;
    list)
        list_backups
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo "Неизвестная команда: $1"
        echo ""
        usage
        exit 1
        ;;
esac
