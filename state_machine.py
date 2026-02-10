# -*- coding: utf-8 -*-
"""
Машина состояний для RelayBot
Управляет поведением робота через дискретные состояния и переходы между ними
"""

import logging
import time
from enum import Enum
from typing import Optional
from navigation import Position, StateContext
import config


class State(Enum):
    """
    Перечисление состояний робота
    
    Состояния представляют различные фазы цикла доставки:
    - WAITING: Ожидание клиента в домашней позиции
    - APPROACHING: Движение к обнаруженному клиенту
    - VERIFYING: Проверка заказа через QR код
    - NAVIGATING_TO_WAREHOUSE: Навигация к зоне загрузки склада
    - LOADING: Ожидание загрузки посылки на складе
    - RETURNING_TO_CUSTOMER: Возврат к клиенту с посылкой
    - DELIVERING: Доставка посылки клиенту
    - RESETTING: Возврат в домашнюю позицию после доставки
    - ERROR_RECOVERY: Восстановление после ошибки
    - EMERGENCY_STOP: Экстренная остановка при критических ошибках (требует ручного вмешательства)
    """
    WAITING = "WAITING"
    APPROACHING = "APPROACHING"
    VERIFYING = "VERIFYING"
    NAVIGATING_TO_WAREHOUSE = "NAVIGATING_TO_WAREHOUSE"
    LOADING = "LOADING"
    RETURNING_TO_CUSTOMER = "RETURNING_TO_CUSTOMER"
    DELIVERING = "DELIVERING"
    RESETTING = "RESETTING"
    ERROR_RECOVERY = "ERROR_RECOVERY"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class StateMachine:
    """
    Машина состояний для управления поведением робота доставки
    
    Координирует действия между подсистемами навигации, аудио, проверки заказов,
    последовательной связи, LiDAR и контроллера коробки.
    """
    
    def __init__(self, navigation, audio, order_verifier, serial_comm, lidar, box_controller):
        """
        Инициализация машины состояний
        
        Args:
            navigation: Система навигации (NavigationSystem)
            audio: Аудио система (AudioSystem)
            order_verifier: Система проверки заказов (OrderVerificationSystem)
            serial_comm: Последовательная связь с Arduino (serialConnection)
            lidar: Интерфейс LiDAR (LiDARInterface)
            box_controller: Контроллер коробки (BoxController)
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Инициализация машины состояний")
        
        # Ссылки на подсистемы
        self.navigation = navigation
        self.audio = audio
        self.order_verifier = order_verifier
        self.serial = serial_comm
        self.lidar = lidar
        self.box_controller = box_controller
        
        # Текущее состояние
        self.current_state = State.WAITING
        
        # Контекст состояния
        self.context = StateContext(
            current_position=Position(0.0, 0.0, 0.0),
            target_position=None,
            customer_position=None,
            current_order_id=None,
            error_message=None
        )
        
        # Время входа в текущее состояние (для таймаутов)
        self.state_entry_time = time.time()
        
        # Счетчик попыток восстановления после ошибок
        self.recovery_attempts = 0
        
        # Флаг для остановки машины состояний
        self.is_running = False
        
        # Счетчик для пропуска обновлений локализации (оптимизация)
        self._localization_skip_counter = 0
        self._localization_skip_rate = 2  # Обновлять локализацию каждую 2-ю итерацию
        
        self.logger.info(f"Машина состояний инициализирована в состоянии {self.current_state.value}")
    
    def transition_to(self, new_state: State) -> None:
        """
        Переход в новое состояние с логированием
        
        Args:
            new_state: Новое состояние для перехода
        """
        old_state = self.current_state
        self.current_state = new_state
        self.state_entry_time = time.time()
        
        self.logger.info(f"Переход состояния: {old_state.value} -> {new_state.value}")
        
        # Отправка соответствующей LED команды при переходе
        self._send_led_command_for_state(new_state)
    
    def _send_led_command_for_state(self, state: State) -> None:
        """
        Отправка LED команды соответствующей состоянию
        
        Args:
            state: Состояние для которого нужно отправить LED команду
        """
        try:
            if state == State.WAITING:
                self.serial.send_led_command("LED_IDLE")
            elif state in [State.APPROACHING, State.NAVIGATING_TO_WAREHOUSE, 
                          State.RETURNING_TO_CUSTOMER, State.RESETTING]:
                self.serial.send_led_command("LED_MOVING")
            elif state in [State.VERIFYING, State.LOADING, State.DELIVERING]:
                self.serial.send_led_command("LED_WAITING")
            elif state in [State.ERROR_RECOVERY, State.EMERGENCY_STOP]:
                self.serial.send_led_command("LED_ERROR")
        except Exception as e:
            self.logger.error(f"Ошибка отправки LED команды: {e}")
    
    def handle_error(self, error: Exception) -> None:
        """
        Обработка ошибок и переход в безопасное состояние
        
        Критические ошибки приводят к экстренной остановке.
        Некритические ошибки приводят к попытке восстановления.
        
        Args:
            error: Исключение, которое нужно обработать
        """
        # Определение критических ошибок
        critical_errors = ()
        try:
            from navigation import (NavigationError, LocalizationFailureError, 
                                   PathPlanningFailureError, GoalUnreachableError, 
                                   ObstacleCollisionError)
            from serialConnection import SerialCommunicationError, SerialTimeoutError
            
            # Проверка на критические ошибки, требующие экстренной остановки
            # Фильтруем None значения на случай неудачного импорта
            error_classes = [LocalizationFailureError, SerialCommunicationError]
            critical_errors = tuple(cls for cls in error_classes if cls is not None)
        except (ImportError, AttributeError) as e:
            # Если импорт не удался, используем пустой кортеж
            self.logger.warning(f"Не удалось импортировать классы ошибок: {e}")
            critical_errors = ()
        
        self.logger.error(f"Обработка ошибки: {error}", exc_info=True)
        
        # Сохранение сообщения об ошибке в контексте
        self.context.error_message = str(error)
        
        # Увеличение счетчика попыток восстановления
        self.recovery_attempts += 1
        
        # Если слишком много попыток восстановления, переходим в экстренную остановку
        if self.recovery_attempts >= config.MAX_RECOVERY_ATTEMPTS:
            self.enter_emergency_stop(
                f"Превышено максимальное количество попыток восстановления ({config.MAX_RECOVERY_ATTEMPTS}): {error}"
            )
            return
        
        # Если это критическая ошибка, переходим в экстренную остановку
        if critical_errors:
            try:
                if isinstance(error, critical_errors):
                    self.enter_emergency_stop(f"Критическая ошибка: {error}")
                    return
            except TypeError:
                # isinstance может выбросить TypeError если в кортеже есть None
                pass
        
        # Для некритических ошибок пытаемся восстановиться
        if self.current_state != State.ERROR_RECOVERY and self.current_state != State.EMERGENCY_STOP:
            self.transition_to(State.ERROR_RECOVERY)
    
    def _check_state_timeout(self) -> bool:
        """
        Проверка таймаута текущего состояния
        
        Returns:
            True если таймаут превышен, False иначе
        """
        elapsed_time = time.time() - self.state_entry_time
        
        # Получение таймаута для текущего состояния
        timeout_map = {
            State.WAITING: config.STATE_TIMEOUT_WAITING,
            State.APPROACHING: config.STATE_TIMEOUT_APPROACHING,
            State.VERIFYING: config.STATE_TIMEOUT_VERIFYING,
            State.NAVIGATING_TO_WAREHOUSE: config.STATE_TIMEOUT_NAVIGATING_TO_WAREHOUSE,
            State.LOADING: config.STATE_TIMEOUT_LOADING,
            State.RETURNING_TO_CUSTOMER: config.STATE_TIMEOUT_RETURNING_TO_CUSTOMER,
            State.DELIVERING: config.STATE_TIMEOUT_DELIVERING,
            State.RESETTING: config.STATE_TIMEOUT_RESETTING,
            State.ERROR_RECOVERY: config.STATE_TIMEOUT_ERROR_RECOVERY,
            State.EMERGENCY_STOP: 0  # Нет таймаута для экстренной остановки
        }
        
        timeout = timeout_map.get(self.current_state, 0)
        
        # Таймаут 0 означает отсутствие ограничения
        if timeout > 0 and elapsed_time > timeout:
            self.logger.warning(f"Таймаут состояния {self.current_state.value}: {elapsed_time:.1f}с > {timeout}с")
            return True
        
        return False
    
    def update(self) -> None:
        """
        Обновление текущего состояния (вызывается в главном цикле)
        
        Вызывает соответствующий обработчик состояния и обрабатывает исключения
        """
        try:
            # Проверка таймаута состояния
            if self._check_state_timeout():
                raise TimeoutError(f"Таймаут состояния {self.current_state.value}")
            
            # Обновление локализации (с пропуском для производительности)
            self._localization_skip_counter += 1
            if self._localization_skip_counter >= self._localization_skip_rate:
                self._localization_skip_counter = 0
                self.navigation.update_localization()
            
            # Обновление текущей позиции в контексте
            x, y, theta = self.navigation.get_current_position()
            self.context.current_position = Position(x, y, theta)
            
            # Вызов обработчика текущего состояния
            if self.current_state == State.WAITING:
                self.update_waiting_state()
            elif self.current_state == State.APPROACHING:
                self.update_approaching_state()
            elif self.current_state == State.VERIFYING:
                self.update_verifying_state()
            elif self.current_state == State.NAVIGATING_TO_WAREHOUSE:
                self.update_navigating_to_warehouse_state()
            elif self.current_state == State.LOADING:
                self.update_loading_state()
            elif self.current_state == State.RETURNING_TO_CUSTOMER:
                self.update_returning_to_customer_state()
            elif self.current_state == State.DELIVERING:
                self.update_delivering_state()
            elif self.current_state == State.RESETTING:
                self.update_resetting_state()
            elif self.current_state == State.ERROR_RECOVERY:
                self.update_error_recovery_state()
            elif self.current_state == State.EMERGENCY_STOP:
                self.update_emergency_stop_state()
            else:
                self.logger.error(f"Неизвестное состояние: {self.current_state}")
                
        except Exception as e:
            self.handle_error(e)
    
    def update_waiting_state(self) -> None:
        """
        Обновление состояния WAITING
        
        Робот находится в домашней позиции и ожидает обнаружения клиента.
        Мониторит LiDAR для обнаружения человека в зоне доставки.
        """
        # Debounce: проверяем не слишком ли часто обнаруживаем
        current_time = time.time()
        if not hasattr(self, '_last_detection_time'):
            self._last_detection_time = 0
        
        # Обнаружение человека в зоне доставки
        person_position = self.lidar.detect_person()
        
        if person_position is not None:
            # Debounce: игнорируем обнаружения чаще чем раз в 2 секунды
            if current_time - self._last_detection_time < 2.0:
                return
            
            self._last_detection_time = current_time
            
            # Для прототипа: любой обнаруженный человек считается клиентом
            global_x = self.context.current_position.x + person_position[0]
            global_y = self.context.current_position.y + person_position[1]
            
            self.logger.info(f"Обнаружен человек в зоне доставки: ({global_x:.2f}, {global_y:.2f})")
            
            # Сохранение позиции клиента как целевой
            self.context.target_position = Position(global_x, global_y, 0.0)
            
            # Переход к подходу к клиенту
            self.transition_to(State.APPROACHING)
    
    def update_approaching_state(self) -> None:
        """
        Обновление состояния APPROACHING
        
        Робот движется к обнаруженному клиенту.
        Непрерывно отслеживает позицию клиента и проверяет расстояние.
        """
        # Проверка наличия целевой позиции
        if self.context.target_position is None:
            self.logger.error("Нет целевой позиции для подхода")
            self.transition_to(State.WAITING)
            return
        
        # Отслеживание клиента с помощью LiDAR
        person_position = self.lidar.detect_person()
        
        if person_position is None:
            # Человек вышел за пределы LIDAR_MAX_RANGE
            self.logger.info("Человек вышел за пределы зоны обнаружения")
            self.navigation.stop()
            
            # Переход к проверке заказа (запрос QR будет в VERIFYING)
            self.transition_to(State.VERIFYING)
            return
        
        # Расстояние до человека (person_position[0] это расстояние)
        distance_to_customer = person_position[0]
        
        # Проверка достижения минимального безопасного расстояния
        if distance_to_customer < config.CUSTOMER_APPROACH_DISTANCE:
            self.logger.info(f"Достигнуто минимальное расстояние: {distance_to_customer:.2f}м")
            self.navigation.stop()
            
            # Сохранение позиции клиента для возврата
            self.context.customer_position = Position(
                self.context.current_position.x,
                self.context.current_position.y,
                self.context.current_position.theta
            )
            
            # Переход к проверке заказа (запрос QR будет в VERIFYING)
            self.transition_to(State.VERIFYING)
            return
        
        # Следование за человеком - простое движение вперед
        base_speed = 120
        
        # Отправка команды движения
        try:
            self.serial.send_motor_command(base_speed, base_speed, 0, 0)
        except Exception as e:
            self.logger.error(f"Ошибка отправки команды движения: {e}")
            self.navigation.stop()
            self.transition_to(State.ERROR_RECOVERY)
    
    def update_verifying_state(self) -> None:
        """
        Обновление состояния VERIFYING
        
        Робот запрашивает QR код у клиента и проверяет заказ.
        """
        # Проверка, был ли уже запущен процесс сканирования
        if not hasattr(self, '_verifying_started'):
            self._verifying_started = True
            self._verification_callback_received = False
            
            # Воспроизведение запроса QR кода
            self.audio.request_qr_code()
            
            # Запуск сканирования QR кода с callback
            self.order_verifier.start_scanning(self._on_qr_scan_result)
            
            self.logger.info("Запущено сканирование QR кода")
        
        # Ожидание результата сканирования (callback установит флаг)
        # Таймаут обрабатывается через _check_state_timeout()
    
    def _on_qr_scan_result(self, is_valid: bool, order_id: Optional[int]) -> None:
        """
        Callback для результата сканирования QR кода
        
        Args:
            is_valid: True если заказ валиден
            order_id: ID заказа (может быть None)
        """
        if self._verification_callback_received:
            return  # Игнорируем повторные вызовы
        
        self._verification_callback_received = True
        
        # Остановка сканирования будет выполнена в основном потоке
        # Здесь только устанавливаем флаг
        
        if is_valid and order_id is not None:
            self.logger.info(f"Заказ {order_id} успешно проверен")
            
            # Сохранение ID заказа
            self.context.current_order_id = order_id
            
            # Воспроизведение звука успеха
            self.audio.announce_order_accepted()
            
            # Остановка сканирования (безопасно из основного потока)
            self.order_verifier.stop_scanning()
            
            # Переход к навигации на склад
            self.transition_to(State.NAVIGATING_TO_WAREHOUSE)
        else:
            self.logger.warning(f"Заказ не прошел проверку: order_id={order_id}")
            
            # Воспроизведение звука неудачи
            self.audio.announce_order_rejected()
            
            # Остановка сканирования (безопасно из основного потока)
            self.order_verifier.stop_scanning()
            
            # Возврат в состояние ожидания
            self.transition_to(State.WAITING)
        
        # Сброс флагов для следующего использования
        delattr(self, '_verifying_started')
        self._verification_callback_received = False
    
    def update_navigating_to_warehouse_state(self) -> None:
        """
        Обновление состояния NAVIGATING_TO_WAREHOUSE
        
        Робот навигирует к зоне загрузки склада.
        """
        # Проверка, была ли уже запущена навигация
        if not hasattr(self, '_warehouse_nav_started'):
            self._warehouse_nav_started = True
            
            # Запуск навигации к складу в отдельном потоке
            import threading
            self._warehouse_nav_thread = threading.Thread(
                target=self._navigate_to_warehouse_thread,
                daemon=True
            )
            self._warehouse_nav_thread.start()
            
            self.logger.info("Запущена навигация к складу")
        
        # Проверка завершения навигации
        if hasattr(self, '_warehouse_nav_result'):
            success = self._warehouse_nav_result
            
            # Очистка флагов
            delattr(self, '_warehouse_nav_started')
            delattr(self, '_warehouse_nav_result')
            
            if success:
                self.logger.info("Достигнута зона загрузки склада")
                self.transition_to(State.LOADING)
            else:
                self.logger.error("Не удалось достичь склада")
                raise RuntimeError("Навигация к складу не удалась")
    
    def _navigate_to_warehouse_thread(self) -> None:
        """
        Поток навигации к складу
        """
        try:
            success = self.navigation.navigate_to(
                config.WAREHOUSE_ZONE[0],
                config.WAREHOUSE_ZONE[1]
            )
            self._warehouse_nav_result = success
        except Exception as e:
            self.logger.error(f"Ошибка навигации к складу: {e}")
            self._warehouse_nav_result = False
    
    def update_loading_state(self) -> None:
        """
        Обновление состояния LOADING
        
        Робот ожидает загрузки посылки на складе.
        """
        # Проверка, было ли уже выполнено объявление
        if not hasattr(self, '_loading_announced'):
            self._loading_announced = True
            
            # Объявление номера заказа
            if self.context.current_order_id is not None:
                self.audio.announce_order_number(self.context.current_order_id)
            
            # Открытие коробки для загрузки
            self.box_controller.open()
            
            self.logger.info("Ожидание загрузки посылки")
            
            # Запуск ожидания подтверждения загрузки
            import threading
            self._loading_thread = threading.Thread(
                target=self._wait_for_loading_confirmation,
                daemon=True
            )
            self._loading_thread.start()
        
        # Проверка завершения загрузки
        if hasattr(self, '_loading_confirmed'):
            confirmed = self._loading_confirmed
            
            # Очистка флагов
            delattr(self, '_loading_announced')
            delattr(self, '_loading_confirmed')
            
            if confirmed:
                # Закрытие коробки
                self.box_controller.close()
                
                self.logger.info("Загрузка завершена, возврат к клиенту")
                self.transition_to(State.RETURNING_TO_CUSTOMER)
            else:
                self.logger.warning("Таймаут загрузки")
                # Закрытие коробки
                self.box_controller.close()
                # Возврат в состояние ожидания
                self.transition_to(State.WAITING)
    
    def _wait_for_loading_confirmation(self) -> None:
        """
        Ожидание подтверждения загрузки (в отдельном потоке)
        
        Ожидает нажатия клавиши Enter или таймаута
        """
        import select
        import sys
        
        try:
            self.logger.info("Нажмите Enter для подтверждения загрузки...")
            
            # Ожидание ввода с таймаутом
            timeout = config.LOADING_CONFIRMATION_TIMEOUT
            
            # Для Windows используем простой input с таймаутом через threading
            import threading
            
            result = [False]
            
            def wait_input():
                try:
                    input()  # Ожидание Enter
                    result[0] = True
                except:
                    pass
            
            input_thread = threading.Thread(target=wait_input, daemon=True)
            input_thread.start()
            input_thread.join(timeout=timeout)
            
            self._loading_confirmed = result[0]
            
        except Exception as e:
            self.logger.error(f"Ошибка ожидания подтверждения загрузки: {e}")
            self._loading_confirmed = False
    
    def update_returning_to_customer_state(self) -> None:
        """
        Обновление состояния RETURNING_TO_CUSTOMER
        
        Робот возвращается к клиенту с посылкой.
        """
        # Проверка наличия сохраненной позиции клиента
        if self.context.customer_position is None:
            self.logger.error("Нет сохраненной позиции клиента")
            raise RuntimeError("Отсутствует позиция клиента для возврата")
        
        # Проверка, была ли уже запущена навигация
        if not hasattr(self, '_return_nav_started'):
            self._return_nav_started = True
            
            # Запуск навигации к клиенту в отдельном потоке
            import threading
            self._return_nav_thread = threading.Thread(
                target=self._navigate_to_customer_thread,
                daemon=True
            )
            self._return_nav_thread.start()
            
            self.logger.info(f"Запущена навигация к клиенту: ({self.context.customer_position.x:.2f}, {self.context.customer_position.y:.2f})")
        
        # Проверка завершения навигации
        if hasattr(self, '_return_nav_result'):
            success = self._return_nav_result
            
            # Очистка флагов
            delattr(self, '_return_nav_started')
            delattr(self, '_return_nav_result')
            
            if success:
                self.logger.info("Достигнута позиция клиента")
                self.transition_to(State.DELIVERING)
            else:
                self.logger.error("Не удалось вернуться к клиенту")
                raise RuntimeError("Навигация к клиенту не удалась")
    
    def _navigate_to_customer_thread(self) -> None:
        """
        Поток навигации к клиенту
        """
        try:
            success = self.navigation.navigate_to(
                self.context.customer_position.x,
                self.context.customer_position.y
            )
            self._return_nav_result = success
        except Exception as e:
            self.logger.error(f"Ошибка навигации к клиенту: {e}")
            self._return_nav_result = False
    
    def update_delivering_state(self) -> None:
        """
        Обновление состояния DELIVERING
        
        Робот доставляет посылку клиенту.
        """
        # Проверка, было ли уже начато приветствие
        if not hasattr(self, '_delivery_started'):
            self._delivery_started = True
            self._delivery_start_time = time.time()
            
            # Приветствие клиента
            self.audio.greet_delivery()
            
            # Открытие коробки
            self.box_controller.open()
            
            self.logger.info(f"Начата доставка, ожидание {config.DELIVERY_TIMEOUT}с")
        
        # Проверка истечения времени доставки
        elapsed_time = time.time() - self._delivery_start_time
        
        if elapsed_time >= config.DELIVERY_TIMEOUT:
            # Закрытие коробки
            self.box_controller.close()
            
            # Очистка флагов
            delattr(self, '_delivery_started')
            delattr(self, '_delivery_start_time')
            
            self.logger.info("Доставка завершена")
            self.transition_to(State.RESETTING)
    
    def update_resetting_state(self) -> None:
        """
        Обновление состояния RESETTING
        
        Робот возвращается в домашнюю позицию после доставки.
        """
        # Проверка, была ли уже запущена навигация
        if not hasattr(self, '_reset_nav_started'):
            self._reset_nav_started = True
            
            # Очистка контекста
            self.context.target_position = None
            self.context.customer_position = None
            self.context.current_order_id = None
            self.context.error_message = None
            
            # Запуск навигации домой в отдельном потоке
            import threading
            self._reset_nav_thread = threading.Thread(
                target=self._navigate_to_home_thread,
                daemon=True
            )
            self._reset_nav_thread.start()
            
            self.logger.info("Запущена навигация домой")
        
        # Проверка завершения навигации
        if hasattr(self, '_reset_nav_result'):
            success = self._reset_nav_result
            
            # Очистка флагов
            delattr(self, '_reset_nav_started')
            delattr(self, '_reset_nav_result')
            
            if success:
                self.logger.info("Достигнута домашняя позиция")
                self.transition_to(State.WAITING)
            else:
                self.logger.error("Не удалось вернуться домой")
                raise RuntimeError("Навигация домой не удалась")
    
    def _navigate_to_home_thread(self) -> None:
        """
        Поток навигации домой
        """
        try:
            success = self.navigation.navigate_to(
                config.HOME_POSITION[0],
                config.HOME_POSITION[1]
            )
            self._reset_nav_result = success
        except Exception as e:
            self.logger.error(f"Ошибка навигации домой: {e}")
            self._reset_nav_result = False
    
    def update_error_recovery_state(self) -> None:
        """
        Обновление состояния ERROR_RECOVERY
        
        Робот восстанавливается после ошибки и возвращается в безопасное состояние.
        """
        # Проверка, было ли уже начато восстановление
        if not hasattr(self, '_recovery_started'):
            self._recovery_started = True
            
            self.logger.warning(f"Начато восстановление после ошибки (попытка {self.recovery_attempts}/{config.MAX_RECOVERY_ATTEMPTS})")
            
            # Остановка всех движений
            self.navigation.stop()
            
            # Закрытие коробки если открыта
            try:
                if self.box_controller.is_open():
                    self.box_controller.close()
            except Exception as e:
                self.logger.error(f"Ошибка закрытия коробки при восстановлении: {e}")
            
            # Воспроизведение звука ошибки
            try:
                self.audio.play_error_sound()
            except Exception as e:
                self.logger.error(f"Ошибка воспроизведения звука ошибки: {e}")
            
            # Проверка количества попыток восстановления
            if self.recovery_attempts >= config.MAX_RECOVERY_ATTEMPTS:
                self.logger.critical("Превышено максимальное количество попыток восстановления")
                self.logger.critical("Требуется ручное вмешательство")
                # Остановка машины состояний
                self.stop()
                return
            
            # Запуск навигации домой для восстановления
            import threading
            self._recovery_nav_thread = threading.Thread(
                target=self._recovery_navigate_to_home_thread,
                daemon=True
            )
            self._recovery_nav_thread.start()
        
        # Проверка завершения навигации восстановления
        if hasattr(self, '_recovery_nav_result'):
            success = self._recovery_nav_result
            
            # Очистка флагов
            delattr(self, '_recovery_started')
            delattr(self, '_recovery_nav_result')
            
            if success:
                self.logger.info("Восстановление успешно, возврат в состояние WAITING")
                
                # Сброс счетчика попыток восстановления
                self.recovery_attempts = 0
                
                # Очистка контекста
                self.context.target_position = None
                self.context.customer_position = None
                self.context.current_order_id = None
                self.context.error_message = None
                
                # Переход в состояние ожидания
                self.transition_to(State.WAITING)
            else:
                self.logger.error("Восстановление не удалось")
                
                # Увеличение счетчика попыток
                self.recovery_attempts += 1
                
                # Повторная попытка через задержку
                time.sleep(config.RECOVERY_RETRY_DELAY)
                
                # Сброс флага для повторной попытки
                if hasattr(self, '_recovery_started'):
                    delattr(self, '_recovery_started')
    
    def _recovery_navigate_to_home_thread(self) -> None:
        """
        Поток навигации домой для восстановления
        """
        try:
            self.logger.info("Попытка навигации домой для восстановления")
            success = self.navigation.navigate_to(
                config.HOME_POSITION[0],
                config.HOME_POSITION[1]
            )
            self._recovery_nav_result = success
        except Exception as e:
            self.logger.error(f"Ошибка навигации домой при восстановлении: {e}")
            self._recovery_nav_result = False
    
    def start(self) -> None:
        """
        Запуск машины состояний
        """
        self.logger.info("Запуск машины состояний")
        self.is_running = True
        
        # Переход в начальное состояние WAITING
        self.transition_to(State.WAITING)
    
    def update_emergency_stop_state(self) -> None:
        """
        Обновление состояния EMERGENCY_STOP
        
        Экстренная остановка при критических ошибках.
        Робот остается в этом состоянии до ручного вмешательства.
        Все системы остановлены, требуется перезапуск.
        """
        # Убедиться что все системы остановлены
        try:
            self.navigation.stop()
        except Exception as e:
            self.logger.error(f"Ошибка остановки навигации в EMERGENCY_STOP: {e}")
        
        try:
            if self.box_controller.is_open():
                self.box_controller.emergency_close()
        except Exception as e:
            self.logger.error(f"Ошибка закрытия коробки в EMERGENCY_STOP: {e}")
        
        # Логирование каждые 10 секунд
        if not hasattr(self, '_last_emergency_log_time'):
            self._last_emergency_log_time = time.time()
        
        if time.time() - self._last_emergency_log_time > 10.0:
            self.logger.critical("ЭКСТРЕННАЯ ОСТАНОВКА: Требуется ручное вмешательство для перезапуска системы")
            self._last_emergency_log_time = time.time()
        
        # Ничего не делаем, ждем ручного вмешательства
        time.sleep(1.0)
    
    def enter_emergency_stop(self, reason: str) -> None:
        """
        Переход в состояние экстренной остановки
        
        Args:
            reason: Причина экстренной остановки
        """
        self.logger.critical(f"ПЕРЕХОД В ЭКСТРЕННУЮ ОСТАНОВКУ: {reason}")
        
        # Остановка всех систем
        try:
            self.navigation.stop()
        except Exception as e:
            self.logger.error(f"Ошибка остановки навигации: {e}")
        
        try:
            if self.box_controller.is_open():
                self.box_controller.emergency_close()
        except Exception as e:
            self.logger.error(f"Ошибка экстренного закрытия коробки: {e}")
        
        # Переход в состояние EMERGENCY_STOP
        self.transition_to(State.EMERGENCY_STOP)
    
    def stop(self) -> None:
        """
        Остановка машины состояний
        """
        self.logger.info("Остановка машины состояний")
        self.is_running = False
        
        # Остановка навигации
        self.navigation.stop()
        
        # Закрытие коробки
        try:
            self.box_controller.close()
        except Exception as e:
            self.logger.error(f"Ошибка закрытия коробки при остановке: {e}")
