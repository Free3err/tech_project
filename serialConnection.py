import serial
import time
import logging
from typing import Optional, Dict, Any
from collections import deque


# ============================================================================
# ИСКЛЮЧЕНИЯ ДЛЯ ПОСЛЕДОВАТЕЛЬНОЙ СВЯЗИ
# ============================================================================

class SerialCommunicationError(Exception):
    """Базовое исключение для ошибок последовательной связи"""
    pass


class SerialTimeoutError(SerialCommunicationError):
    """Ошибка таймаута последовательной связи"""
    pass


class CommandQueueOverflowError(SerialCommunicationError):
    """Ошибка переполнения очереди команд"""
    pass


# ============================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================================================

ser = None
logger = logging.getLogger(__name__)

# Очередь команд для управления переполнением
command_queue = deque(maxlen=10)  # Максимум 10 команд в очереди

# Счетчики ошибок
serial_timeout_count = 0
serial_error_count = 0
last_successful_communication = time.time()

def init_serial(port='COM10', baudrate=9600):
    """
    Инициализация последовательного соединения с Arduino
    
    Args:
        port: Порт последовательного соединения (COM10 для Windows, /dev/ttyACM0 для Linux)
        baudrate: Скорость передачи данных (по умолчанию 9600)
        
    Raises:
        SerialCommunicationError: Если не удалось установить соединение
    """
    global ser, logger, last_successful_communication
    
    try:
        ser = serial.Serial(port, baudrate, timeout=1.0)
        time.sleep(2)  # Ожидание инициализации Arduino
        logger.info(f"Последовательное соединение установлено на порту {port}")
        last_successful_communication = time.time()
    except serial.SerialException as e:
        logger.error(f"Ошибка инициализации последовательного соединения: {e}")
        raise SerialCommunicationError(f"Не удалось подключиться к порту {port}: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка инициализации: {e}")
        raise SerialCommunicationError(f"Критическая ошибка инициализации: {e}")


def _send_command_with_retry(command: str, max_retries: int = 3) -> bool:
    """
    Отправка команды с повторными попытками и экспоненциальной задержкой
    
    Args:
        command: Команда для отправки
        max_retries: Максимальное количество попыток
        
    Returns:
        True если команда отправлена успешно, False иначе
        
    Raises:
        SerialTimeoutError: Если все попытки исчерпаны
    """
    global ser, logger, serial_timeout_count, serial_error_count, last_successful_communication
    
    if ser is None:
        raise RuntimeError("Serial connection not initialized. Call init_serial() first.")
    
    for attempt in range(max_retries):
        try:
            ser.write(command.encode())
            
            # Ожидание подтверждения (опционально)
            # В текущей реализации Arduino не всегда отправляет ACK
            
            # Успешная отправка
            last_successful_communication = time.time()
            if serial_timeout_count > 0 or serial_error_count > 0:
                logger.info("Связь с Arduino восстановлена")
                serial_timeout_count = 0
                serial_error_count = 0
            
            return True
            
        except serial.SerialTimeoutException as e:
            serial_timeout_count += 1
            logger.warning(f"Таймаут отправки команды (попытка {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                # Экспоненциальная задержка
                delay = 0.1 * (2 ** attempt)
                time.sleep(delay)
            else:
                logger.error(f"Не удалось отправить команду после {max_retries} попыток")
                raise SerialTimeoutError(f"Таймаут отправки команды: {command}")
                
        except serial.SerialException as e:
            serial_error_count += 1
            logger.error(f"Ошибка последовательной связи (попытка {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                # Попытка переподключения
                try:
                    ser.close()
                    time.sleep(0.5)
                    ser.open()
                    logger.info("Переподключение успешно")
                except Exception as reconnect_error:
                    logger.error(f"Ошибка переподключения: {reconnect_error}")
            else:
                raise SerialCommunicationError(f"Ошибка связи: {e}")
                
        except Exception as e:
            serial_error_count += 1
            logger.error(f"Неожиданная ошибка отправки команды: {e}")
            if attempt == max_retries - 1:
                raise SerialCommunicationError(f"Критическая ошибка отправки: {e}")
    
    return False


def send_motor_command(left_speed: int, right_speed: int, left_dir: int, right_dir: int) -> None:
    """
    Отправить команду управления моторами с повторными попытками
    
    Args:
        left_speed: Скорость левого мотора (0-255)
        right_speed: Скорость правого мотора (0-255)
        left_dir: Направление левого мотора (0 или 1)
        right_dir: Направление правого мотора (0 или 1)
    
    Raises:
        ValueError: Если параметры вне допустимого диапазона
        RuntimeError: Если последовательное соединение не инициализировано
        SerialTimeoutError: Если не удалось отправить команду после повторных попыток
    """
    global ser
    
    if ser is None:
        raise RuntimeError("Serial connection not initialized. Call init_serial() first.")
    
    # Проверка диапазонов параметров
    if not (0 <= left_speed <= 255):
        raise ValueError(f"left_speed must be 0-255, got {left_speed}")
    if not (0 <= right_speed <= 255):
        raise ValueError(f"right_speed must be 0-255, got {right_speed}")
    if left_dir not in (0, 1):
        raise ValueError(f"left_dir must be 0 or 1, got {left_dir}")
    if right_dir not in (0, 1):
        raise ValueError(f"right_dir must be 0 or 1, got {right_dir}")
    
    # Формирование команды
    command = f"MOTOR:{left_speed},{right_speed},{left_dir},{right_dir}\n"
    
    # Логирование команды мотора
    logger.debug(f"Отправка команды мотора: L={left_speed}({left_dir}) R={right_speed}({right_dir})")
    
    # Отправка с повторными попытками
    _send_command_with_retry(command)


def send_servo_command(angle: int) -> None:
    """
    Отправить команду сервоприводу с повторными попытками
    
    Args:
        angle: Угол сервопривода (0-90 градусов)
    
    Raises:
        ValueError: Если угол вне допустимого диапазона
        RuntimeError: Если последовательное соединение не инициализировано
        SerialTimeoutError: Если не удалось отправить команду после повторных попыток
    """
    global ser
    
    if ser is None:
        raise RuntimeError("Serial connection not initialized. Call init_serial() first.")
    
    # Проверка диапазона угла
    if not (0 <= angle <= 90):
        raise ValueError(f"angle must be 0-90, got {angle}")
    
    # Формирование команды
    command = f"SERVO:{angle}\n"
    
    # Логирование команды сервопривода
    logger.debug(f"Отправка команды сервопривода: угол={angle}°")
    
    # Отправка с повторными попытками
    _send_command_with_retry(command)


def send_led_command(command: str) -> None:
    """
    Отправить команду LED эффекта с повторными попытками
    
    Args:
        command: Команда LED (SUCCESS_SCAN, FAILURE_SCAN, LED_IDLE, LED_WAITING, LED_MOVING, STOP)
    
    Raises:
        ValueError: Если команда не поддерживается
        RuntimeError: Если последовательное соединение не инициализировано
        SerialTimeoutError: Если не удалось отправить команду после повторных попыток
    """
    global ser
    
    if ser is None:
        raise RuntimeError("Serial connection not initialized. Call init_serial() first.")
    
    # Список поддерживаемых команд
    valid_commands = ['SUCCESS_SCAN', 'FAILURE_SCAN', 'LED_IDLE', 'LED_WAITING', 'LED_MOVING', 'LED_ERROR', 'STOP']
    
    if command not in valid_commands:
        raise ValueError(f"Invalid LED command: {command}. Valid commands: {valid_commands}")
    
    # Формирование команды
    cmd = f"{command}\n"
    
    # Логирование LED команды
    logger.debug(f"Отправка LED команды: {command}")
    
    # Отправка с повторными попытками
    _send_command_with_retry(cmd)


def read_sensor_data(timeout: float = 0.5) -> Optional[Dict[str, Any]]:
    """
    Прочитать данные сенсоров от Arduino с таймаутом
    
    Args:
        timeout: Таймаут чтения в секундах (по умолчанию 0.5)
    
    Returns:
        Словарь с данными сенсоров или None, если данные недоступны
        Возможные ключи:
        - 'ir': расстояние от IR сенсора (см)
        - 'encoder_left': тики левого энкодера
        - 'encoder_right': тики правого энкодера
        - 'ack': подтверждение команды
    
    Raises:
        RuntimeError: Если последовательное соединение не инициализировано
    """
    global ser, logger
    
    if ser is None:
        raise RuntimeError("Serial connection not initialized. Call init_serial() first.")
    
    # Проверка наличия данных
    if ser.in_waiting == 0:
        return None
    
    try:
        # Установка таймаута для чтения
        original_timeout = ser.timeout
        ser.timeout = timeout
        
        # Чтение строки данных
        line = ser.readline().decode('utf-8').strip()
        
        # Восстановление оригинального таймаута
        ser.timeout = original_timeout
        
        if not line:
            return None
        
        # Парсинг данных в зависимости от типа
        if line.startsWith("IR:"):
            # Формат: IR:<distance>
            distance_str = line[3:]
            ir_distance = float(distance_str)
            logger.debug(f"Получены данные IR сенсора: {ir_distance}см")
            return {'ir': ir_distance}
        
        elif line.startswith("ENCODER:"):
            # Формат: ENCODER:<left_ticks>,<right_ticks>
            data = line[8:].split(',')
            if len(data) == 2:
                encoder_data = {
                    'encoder_left': int(data[0]),
                    'encoder_right': int(data[1])
                }
                logger.debug(f"Получены данные энкодеров: L={encoder_data['encoder_left']} R={encoder_data['encoder_right']}")
                return encoder_data
        
        elif line == "ACK":
            # Подтверждение команды
            return {'ack': True}
        
        else:
            # Неизвестный формат данных
            logger.debug(f"Неизвестный формат данных: {line}")
            return {'raw': line}
    
    except serial.SerialTimeoutException:
        logger.warning("Таймаут чтения данных сенсоров")
        return None
    
    except (ValueError, UnicodeDecodeError) as e:
        # Ошибка парсинга данных
        logger.warning(f"Ошибка парсинга данных сенсоров: {e}")
        return {'error': str(e)}
    
    except Exception as e:
        logger.error(f"Неожиданная ошибка чтения данных: {e}")
        return {'error': str(e)}
