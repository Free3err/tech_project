# -*- coding: utf-8 -*-
"""
Главный файл RelayBot - Автономная система доставки
Инициализирует и запускает все подсистемы через машину состояний
"""

import sys
import time
import signal
import logging
from logging.handlers import RotatingFileHandler

# Импорт модулей конфигурации
import config

# Импорт существующих модулей
from db.db import init_db
from serialConnection import init_serial
from qrScanner import OrderVerificationSystem

# Импорт новых модулей
from state_machine import StateMachine
from navigation import NavigationSystem
from lidar_interface import LiDARInterface
from odometry import OdometrySystem
from audio_system import AudioSystem
from box_controller import BoxController


# Глобальные переменные для graceful shutdown
state_machine = None
running = True


def setup_logging():
    """
    Настройка системы логирования
    
    Создает логгеры для записи в файл и вывода в консоль
    с ротацией файлов для предотвращения переполнения диска.
    Создает отдельные файлы логов для разных подсистем.
    """
    # Создание корневого логгера
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для главного файла с ротацией
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=config.LOG_MAX_SIZE,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Создание отдельных файлов логов для подсистем
    subsystems = {
        'state_machine': 'state_machine.log',
        'navigation': 'navigation.log',
        'lidar_interface': 'lidar.log',
        'odometry': 'odometry.log',
        'serialConnection': 'serial.log',
        'audio_system': 'audio.log',
        'box_controller': 'box.log',
        'qrScanner': 'qr_scanner.log'
    }
    
    for subsystem_name, log_file in subsystems.items():
        subsystem_logger = logging.getLogger(subsystem_name)
        subsystem_handler = RotatingFileHandler(
            log_file,
            maxBytes=config.LOG_MAX_SIZE // 2,  # Меньший размер для подсистем
            backupCount=3,
            encoding='utf-8'
        )
        subsystem_handler.setLevel(logging.DEBUG)
        subsystem_handler.setFormatter(formatter)
        subsystem_logger.addHandler(subsystem_handler)
    
    logger.info("=" * 80)
    logger.info("Система логирования инициализирована")
    logger.info("Отдельные файлы логов созданы для подсистем:")
    for subsystem_name, log_file in subsystems.items():
        logger.info(f"  - {subsystem_name}: {log_file}")
    logger.info("=" * 80)


def signal_handler(signum, frame):
    """
    Обработчик сигналов для graceful shutdown
    
    Вызывается при получении SIGINT (Ctrl+C) или SIGTERM
    для корректного завершения работы системы.
    
    Args:
        signum: Номер сигнала
        frame: Текущий фрейм стека
    """
    global running, state_machine
    
    logger = logging.getLogger(__name__)
    logger.info(f"Получен сигнал {signum}, начинается graceful shutdown...")
    
    running = False
    
    # Остановка машины состояний
    if state_machine is not None:
        try:
            state_machine.stop()
        except Exception as e:
            logger.error(f"Ошибка остановки машины состояний: {e}")


def initialize_subsystems():
    """
    Инициализация всех подсистем робота
    
    Инициализирует подсистемы в правильном порядке:
    1. Последовательная связь с Arduino
    2. База данных
    3. LiDAR интерфейс
    4. Система одометрии
    5. Система навигации
    6. Аудио система
    7. Контроллер коробки
    8. Система проверки заказов
    9. Машина состояний
    
    Returns:
        StateMachine: Инициализированная машина состояний
        
    Raises:
        RuntimeError: Если не удалось инициализировать критичные подсистемы
    """
    logger = logging.getLogger(__name__)
    logger.info("Начало инициализации подсистем...")
    
    try:
        # 1. Инициализация последовательной связи с Arduino
        logger.info("Инициализация последовательной связи с Arduino...")
        try:
            init_serial(port=config.ARDUINO_PORT, baudrate=config.ARDUINO_BAUDRATE)
            logger.info(f"✓ Последовательная связь установлена: {config.ARDUINO_PORT}")
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации последовательной связи: {e}")
            raise RuntimeError(f"Не удалось подключиться к Arduino: {e}")
        
        # Импорт модуля после инициализации для доступа к глобальной переменной ser
        import serialConnection
        
        # 2. Инициализация базы данных
        logger.info("Инициализация базы данных...")
        try:
            init_db()
            logger.info("✓ База данных инициализирована")
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации базы данных: {e}")
            raise RuntimeError(f"Не удалось инициализировать базу данных: {e}")
        
        # 3. Инициализация LiDAR интерфейса
        logger.info("Инициализация LiDAR интерфейса...")
        try:
            lidar = LiDARInterface(
                port=config.LIDAR_PORT,
                baudrate=config.LIDAR_BAUDRATE
            )
            logger.info(f"✓ LiDAR подключен: {config.LIDAR_PORT}")
        except Exception as e:
            logger.warning(f"⚠ Не удалось подключить LiDAR: {e}")
            logger.warning("Система будет работать без LiDAR (ограниченная функциональность)")
            # Создаем заглушку для LiDAR (для тестирования без оборудования)
            lidar = None
        
        # 4. Инициализация системы одометрии
        logger.info("Инициализация системы одометрии...")
        odometry = OdometrySystem(
            wheel_base=config.WHEEL_BASE,
            wheel_radius=config.WHEEL_RADIUS
        )
        logger.info("✓ Система одометрии инициализирована")
        
        # 5. Инициализация системы навигации
        logger.info("Инициализация системы навигации...")
        try:
            navigation = NavigationSystem(
                map_file=config.MAP_FILE,
                lidar_interface=lidar,
                odometry=odometry,
                serial_comm=serialConnection
            )
            logger.info(f"✓ Система навигации инициализирована с картой: {config.MAP_FILE}")
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации системы навигации: {e}")
            raise RuntimeError(f"Не удалось инициализировать навигацию: {e}")
        
        # 6. Инициализация аудио системы
        logger.info("Инициализация аудио системы...")
        try:
            audio = AudioSystem(audio_dir=config.AUDIO_DIR)
            logger.info(f"✓ Аудио система инициализирована: {config.AUDIO_DIR}")
        except Exception as e:
            logger.warning(f"⚠ Ошибка инициализации аудио системы: {e}")
            logger.warning("Система будет работать без аудио обратной связи")
            audio = None
        
        # 7. Инициализация контроллера коробки
        logger.info("Инициализация контроллера коробки...")
        try:
            box_controller = BoxController(serial_comm=serialConnection)
            logger.info("✓ Контроллер коробки инициализирован")
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации контроллера коробки: {e}")
            raise RuntimeError(f"Не удалось инициализировать контроллер коробки: {e}")
        
        # 8. Инициализация системы проверки заказов
        logger.info("Инициализация системы проверки заказов...")
        try:
            order_verifier = OrderVerificationSystem(
                db_session=None,  # Использует глобальную сессию
                serial_comm=serialConnection.ser
            )
            logger.info("✓ Система проверки заказов инициализирована")
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации системы проверки заказов: {e}")
            raise RuntimeError(f"Не удалось инициализировать систему проверки заказов: {e}")
        
        # 9. Инициализация машины состояний
        logger.info("Инициализация машины состояний...")
        try:
            sm = StateMachine(
                navigation=navigation,
                audio=audio,
                order_verifier=order_verifier,
                serial_comm=serialConnection,
                lidar=lidar,
                box_controller=box_controller
            )
            logger.info("✓ Машина состояний инициализирована")
        except Exception as e:
            logger.error(f"✗ Ошибка инициализации машины состояний: {e}")
            raise RuntimeError(f"Не удалось инициализировать машину состояний: {e}")
        
        logger.info("=" * 80)
        logger.info("Все подсистемы успешно инициализированы!")
        logger.info("=" * 80)
        
        return sm
        
    except Exception as e:
        logger.critical(f"Критическая ошибка инициализации: {e}")
        raise


def main_loop(sm: StateMachine):
    """
    Главный цикл управления роботом
    
    Вызывает обновление машины состояний с частотой 10 Гц (каждые 0.1 секунды).
    Обрабатывает исключения и обеспечивает graceful shutdown.
    
    Args:
        sm: Машина состояний для управления
    """
    global running
    
    logger = logging.getLogger(__name__)
    logger.info("Запуск главного цикла управления...")
    logger.info(f"Частота обновления: {config.NAVIGATION_UPDATE_RATE} Гц")
    
    # Вычисление периода обновления
    update_period = 1.0 / config.NAVIGATION_UPDATE_RATE  # 0.1 секунды для 10 Гц
    
    # Запуск машины состояний
    sm.start()
    
    # Счетчики для статистики
    iteration_count = 0
    start_time = time.time()
    
    try:
        while running and sm.is_running:
            loop_start = time.time()
            
            # Обновление машины состояний
            try:
                sm.update()
                iteration_count += 1
                
                # Вывод статистики каждые 100 итераций
                if iteration_count % 100 == 0:
                    elapsed = time.time() - start_time
                    actual_rate = iteration_count / elapsed
                    logger.debug(f"Статистика: {iteration_count} итераций, "
                               f"фактическая частота: {actual_rate:.2f} Гц")
                
            except KeyboardInterrupt:
                # Ctrl+C обрабатывается через signal_handler
                raise
            except Exception as e:
                logger.error(f"Ошибка в главном цикле: {e}", exc_info=True)
                # Машина состояний обработает ошибку через handle_error()
            
            # Вычисление времени сна для поддержания частоты 10 Гц
            loop_duration = time.time() - loop_start
            sleep_time = max(0, update_period - loop_duration)
            
            # Предупреждение если цикл выполняется слишком долго
            if loop_duration > update_period:
                logger.warning(f"Цикл выполнялся {loop_duration:.3f}с, "
                             f"превышает период {update_period:.3f}с")
            
            # Сон для поддержания частоты
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания (Ctrl+C)")
    
    finally:
        # Статистика работы
        total_time = time.time() - start_time
        avg_rate = iteration_count / total_time if total_time > 0 else 0
        logger.info(f"Главный цикл завершен: {iteration_count} итераций за {total_time:.2f}с")
        logger.info(f"Средняя частота обновления: {avg_rate:.2f} Гц")


def shutdown(sm: StateMachine):
    """
    Корректное завершение работы системы
    
    Останавливает все подсистемы в обратном порядке инициализации
    и освобождает ресурсы.
    
    Args:
        sm: Машина состояний для остановки
    """
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("Начало процедуры shutdown...")
    logger.info("=" * 80)
    
    try:
        # Остановка машины состояний
        if sm is not None:
            logger.info("Остановка машины состояний...")
            sm.stop()
            logger.info("✓ Машина состояний остановлена")
        
        # Закрытие LiDAR соединения
        if sm and sm.lidar is not None:
            logger.info("Закрытие LiDAR соединения...")
            try:
                sm.lidar.close()
                logger.info("✓ LiDAR соединение закрыто")
            except Exception as e:
                logger.error(f"✗ Ошибка закрытия LiDAR: {e}")
        
        # Остановка камеры QR сканера
        if sm and sm.order_verifier is not None:
            logger.info("Остановка QR сканера...")
            try:
                sm.order_verifier.stop_scanning()
                logger.info("✓ QR сканер остановлен")
            except Exception as e:
                logger.error(f"✗ Ошибка остановки QR сканера: {e}")
        
        # Закрытие последовательного соединения
        logger.info("Закрытие последовательного соединения...")
        try:
            import serialConnection
            if serialConnection.ser is not None and serialConnection.ser.is_open:
                serialConnection.ser.close()
                logger.info("✓ Последовательное соединение закрыто")
        except Exception as e:
            logger.error(f"✗ Ошибка закрытия последовательного соединения: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка во время shutdown: {e}", exc_info=True)
    
    finally:
        logger.info("=" * 80)
        logger.info("Shutdown завершен. RelayBot остановлен.")
        logger.info("=" * 80)


def main():
    """
    Главная функция программы
    
    Выполняет:
    1. Настройку логирования
    2. Регистрацию обработчиков сигналов
    3. Инициализацию подсистем
    4. Запуск главного цикла
    5. Graceful shutdown
    """
    global state_machine
    
    # Настройка логирования
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 80)
    logger.info("ЗАПУСК RELAYBOT - АВТОНОМНАЯ СИСТЕМА ДОСТАВКИ")
    logger.info("=" * 80)
    logger.info(f"Версия Python: {sys.version}")
    logger.info(f"Конфигурация:")
    logger.info(f"  - Домашняя позиция: {config.HOME_POSITION}")
    logger.info(f"  - Зона склада: {config.WAREHOUSE_ZONE}")
    logger.info(f"  - Порт Arduino: {config.ARDUINO_PORT}")
    logger.info(f"  - Порт LiDAR: {config.LIDAR_PORT}")
    logger.info(f"  - Файл карты: {config.MAP_FILE}")
    logger.info("=" * 80)
    
    # Регистрация обработчиков сигналов для graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Обработчики сигналов зарегистрированы (SIGINT, SIGTERM)")
    
    try:
        # Инициализация всех подсистем
        state_machine = initialize_subsystems()
        
        # Запуск главного цикла управления
        main_loop(state_machine)
        
    except KeyboardInterrupt:
        logger.info("Программа прервана пользователем (Ctrl+C)")
    
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        return 1
    
    finally:
        # Корректное завершение работы
        shutdown(state_machine)
    
    logger.info("Программа завершена успешно")
    return 0


if __name__ == '__main__':
    sys.exit(main())
