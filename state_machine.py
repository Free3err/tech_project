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
    - VOICE_VERIFICATION: Голосовая верификация кода перед выдачей
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
    VOICE_VERIFICATION = "VOICE_VERIFICATION"
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
            elif state in [State.VERIFYING, State.LOADING, State.VOICE_VERIFICATION, State.DELIVERING]:
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
            State.VOICE_VERIFICATION: config.STATE_TIMEOUT_VOICE_VERIFICATION,
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
            elif self.current_state == State.VOICE_VERIFICATION:
                self.update_voice_verification_state()
            elif self.current_state == State.DELIVERING:
                # Отладочный лог для проверки вызова
                if not hasattr(self, '_delivering_debug_logged'):
                    self._delivering_debug_logged = True
                    self.logger.info(">>> DEBUG: Вызов update_delivering_state()")
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
        # Проверка доступности LiDAR
        if self.lidar is None:
            self.logger.debug("LiDAR недоступен в WAITING")
            return
        
        # Debounce: проверяем не слишком ли часто обнаруживаем
        current_time = time.time()
        if not hasattr(self, '_last_detection_time'):
            self._last_detection_time = 0
        
        # Обнаружение человека в зоне доставки
        person_position = self.lidar.detect_person()
        
        if person_position is not None:
            # Debounce: игнорируем обнаружения чаще чем раз в 2 секунды
            if current_time - self._last_detection_time < 2.0:
                self.logger.debug(f"Обнаружение проигнорировано (debounce): {current_time - self._last_detection_time:.2f}с")
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
        base_speed = 140
        
        # Отправка команды движения (dir=1 для движения вперед)
        try:
            self.serial.send_motor_command(base_speed, base_speed, 1, 1)
        except Exception as e:
            self.logger.error(f"Ошибка отправки команды движения: {e}")
            self.navigation.stop()
            self.transition_to(State.ERROR_RECOVERY)
    
    def update_verifying_state(self) -> None:
        """
        Обновление состояния VERIFYING
        
        Робот запрашивает QR код у клиента и проверяет заказ.
        Повторяет сканирование пока человек в зоне видимости.
        После успешной проверки ждет 5 секунд перед переходом к LOADING.
        """
        # Проверка задержки после отклонения заказа
        if hasattr(self, '_rejection_delay_start'):
            elapsed = time.time() - self._rejection_delay_start
            if elapsed < self._rejection_delay_duration:
                # Еще ждем
                return
            else:
                # Задержка прошла, убираем флаги и перезапускаем сканирование
                delattr(self, '_rejection_delay_start')
                delattr(self, '_rejection_delay_duration')
                
                # Сбрасываем флаги для перезапуска
                if hasattr(self, '_verifying_started'):
                    delattr(self, '_verifying_started')
                self._verification_callback_received = False
                
                if hasattr(self, '_need_restart_scanning'):
                    delattr(self, '_need_restart_scanning')
                
                self.logger.info("Задержка завершена, перезапуск сканирования")
        
        # Проверка задержки перед переходом к LOADING
        if hasattr(self, '_loading_delay_start'):
            elapsed = time.time() - self._loading_delay_start
            if elapsed >= config.VERIFYING_TO_LOADING_DELAY:
                delattr(self, '_loading_delay_start')
                self.logger.info("Задержка завершена, переход к загрузке")
                self.transition_to(State.LOADING)
            return
        
        # Проверка наличия человека в зоне видимости
        person_position = self.lidar.detect_person()
        
        if person_position is None:
            # Человек ушел - возврат в WAITING
            self.logger.info("Человек вышел из зоны видимости во время верификации")
            
            # Остановка сканирования если оно запущено
            if hasattr(self, '_verifying_started'):
                self.order_verifier.stop_scanning()
                delattr(self, '_verifying_started')
                self._verification_callback_received = False
            
            # Очистка флагов задержки если есть
            if hasattr(self, '_rejection_delay_start'):
                delattr(self, '_rejection_delay_start')
                delattr(self, '_rejection_delay_duration')
            
            self.transition_to(State.WAITING)
            return
        
        # Проверка, был ли уже запущен процесс сканирования
        if not hasattr(self, '_verifying_started'):
            self._verifying_started = True
            self._verification_callback_received = False
            
            # Воспроизведение запроса QR кода только если не было недавнего отклонения
            if not hasattr(self, '_rejection_delay_start'):
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
            
            # Сброс флагов
            delattr(self, '_verifying_started')
            self._verification_callback_received = False
            
            # Установка времени для задержки перед LOADING
            self._loading_delay_start = time.time()
            self.logger.info(f"Ожидание {config.VERIFYING_TO_LOADING_DELAY}с перед загрузкой")
        else:
            self.logger.warning(f"Заказ не прошел проверку: order_id={order_id}")
            
            # Остановка сканирования (безопасно из основного потока)
            self.order_verifier.stop_scanning()
            
            # Воспроизведение звука неудачи
            self.audio.announce_order_rejected()
            
            # Установка времени задержки перед повторным сканированием (5 секунд чтобы аудио успело проиграться)
            self._rejection_delay_start = time.time()
            self._rejection_delay_duration = 5.0  # 5 секунд задержки
            
            # Сброс флагов для повторного сканирования после задержки
            # НЕ удаляем _verifying_started здесь - удалим после задержки
            self._verification_callback_received = False
            self._need_restart_scanning = True  # Флаг что нужно перезапустить сканирование
            
            self.logger.info("Ожидание 5 секунд перед повторным сканированием QR кода")
    
    def update_navigating_to_warehouse_state(self) -> None:
        """
        Обновление состояния NAVIGATING_TO_WAREHOUSE
        
        Пустое состояние - ничего не делает.
        """

        pass
    
    def update_loading_state(self) -> None:
        """
        Обновление состояния LOADING
        
        Погрузка:
        - Произносит номер заказа
        - Ждет таймаут из конфига
        - Озвучивает окончание загрузки
        - Переход к голосовой верификации
        """
        if not hasattr(self, '_loading_started'):
            self._loading_started = True
            self._loading_step_start = time.time()
            
            # Произносит номер заказа
            if self.context.current_order_id is not None:
                self.audio.announce_order_number(self.context.current_order_id)
            
            self.logger.info(f"Ожидание загрузки ({config.LOADING_CONFIRMATION_TIMEOUT}с)")
        
        elapsed = time.time() - self._loading_step_start
        
        # Ожидание таймаута загрузки
        if elapsed >= config.LOADING_CONFIRMATION_TIMEOUT:
            # Озвучка окончания загрузки
            self.audio.announce_loading_complete()
            
            # Очистка флагов
            delattr(self, '_loading_started')
            delattr(self, '_loading_step_start')
            
            self.logger.info("Загрузка завершена, переход к голосовой верификации")
            self.transition_to(State.VOICE_VERIFICATION)
    
    def update_returning_to_customer_state(self) -> None:
        """
        Обновление состояния RETURNING_TO_CUSTOMER
        
        Пустое состояние - ничего не делает.
        """
        pass
    
    def update_voice_verification_state(self) -> None:
        """
        Обновление состояния VOICE_VERIFICATION
        
        Голосовая верификация кода перед выдачей:
        - Ждет 5 секунд после окончания загрузки
        - Запрашивает код голосом
        - Слушает 10 секунд
        - Проверяет код (тестовый: "1111")
        - Если правильно -> DELIVERING
        - Если неправильно -> повторный запрос
        """
        if not hasattr(self, '_voice_verification_started'):
            self._voice_verification_started = True
            self._voice_start_time = time.time()
            self._code_requested = False
            self._listening = False
            
            self.logger.info("Ожидание 5 секунд перед запросом кода")
        
        elapsed = time.time() - self._voice_start_time
        
        # Запрос кода через 5 секунд
        if elapsed >= 5.0 and not self._code_requested:
            self._code_requested = True
            self._request_time = time.time()
            
            # Запрос кода
            self.audio.request_voice_code()
            self.logger.info("Запрос голосового кода")
        
        # Начинаем слушать через 2 секунды после запроса (после озвучки)
        if self._code_requested and not self._listening:
            request_elapsed = time.time() - self._request_time
            if request_elapsed >= 2.0:
                self._listening = True
                self._listen_start_time = time.time()
                self.logger.info("Начало прослушивания голосового кода (10 секунд)")
        
        # Слушаем 10 секунд
        if self._listening:
            listen_elapsed = time.time() - self._listen_start_time


            
            if listen_elapsed >= 4.0:
                # Распознавание речи
                recognized_code = self._recognize_voice_code()
                
                if recognized_code == "2245":
                    # Код правильный
                    self.logger.info("Голосовой код верный")
                    self.audio.announce_code_accepted()
                    
                    # Очистка флагов
                    delattr(self, '_voice_verification_started')
                    delattr(self, '_voice_start_time')
                    delattr(self, '_code_requested')
                    delattr(self, '_request_time')
                    delattr(self, '_listening')
                    delattr(self, '_listen_start_time')
                    
                    self.logger.info("Переход к выдаче заказа")
                    self.transition_to(State.DELIVERING)
                else:
                    # Код неправильный - повторный запрос
                    self.logger.warning(f"Голосовой код неверный: {recognized_code}")
                    self.audio.announce_code_rejected()
                    
                    # Сброс для повторной попытки
                    delattr(self, '_voice_verification_started')
                    delattr(self, '_voice_start_time')
                    delattr(self, '_code_requested')
                    delattr(self, '_request_time')
                    delattr(self, '_listening')
                    delattr(self, '_listen_start_time')
    
    def _recognize_voice_code(self) -> str:
        """
        Распознавание голосового кода с микрофона
        
        Returns:
            Распознанный код или пустая строка
        """
        try:
            import speech_recognition as sr
            
            recognizer = sr.Recognizer()
            
            # Используем микрофон камеры (устройство 1)
            with sr.Microphone(device_index=1) as source:
                self.logger.info("Настройка микрофона...")
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                self.logger.info("Слушаю...")
                # Слушаем без таймаута, записываем до первой паузы (макс 10 сек)
                audio = recognizer.listen(source, phrase_time_limit=7)
                
                self.logger.info("Распознавание...")
                # Распознавание через Google Speech Recognition
                text = recognizer.recognize_google(audio, language='ru-RU')
                self.logger.info(f"Распознан текст: {text}")
                
                # Извлечение цифр из текста
                import re
                digits = re.findall(r'\d+', text)
                if digits:
                    code = ''.join(digits)
                    self.logger.info(f"Извлечен код: {code}")
                    return code
                
                return ""
                
        except sr.WaitTimeoutError:
            self.logger.warning("Таймаут ожидания речи")
            return ""
        except sr.UnknownValueError:
            self.logger.warning("Не удалось распознать речь")
            return ""
        except sr.RequestError as e:
            self.logger.error(f"Ошибка сервиса распознавания: {e}")
            return ""
        except Exception as e:
            self.logger.error(f"Ошибка распознавания речи: {e}")
            return ""
    
    def update_delivering_state(self) -> None:
        """
        Обновление состояния DELIVERING
        
        Выдача посылки клиенту:
        - Ожидание 5 секунд
        - Голосовое сообщение о выдаче
        - Ожидание 10 секунд
        - Переход в WAITING
        """
        if not hasattr(self, '_delivery_started'):
            self._delivery_started = True
            self._delivery_start_time = time.time()
            self._greeting_played = False
            
            self.logger.info("=== DELIVERING STATE: Начало выдачи ===")
            self.logger.info("Ожидание 5 секунд перед голосовым сообщением")
        
        elapsed = time.time() - self._delivery_start_time
        
        # Логирование каждую секунду для отладки
        if not hasattr(self, '_last_log_time'):
            self._last_log_time = 0
        
        if int(elapsed) > self._last_log_time:
            self._last_log_time = int(elapsed)
            self.logger.info(f"DELIVERING: прошло {self._last_log_time} секунд")
        
        # Воспроизведение голосового сообщения через 5 секунд
        if elapsed >= 5.0 and not self._greeting_played:
            self.logger.info("=== 5 секунд прошло, воспроизведение голосового сообщения ===")
            try:
                self.audio.greet_delivery()
                self._greeting_played = True
                self.logger.info("=== Голосовое сообщение воспроизведено успешно ===")
            except Exception as e:
                self.logger.error(f"Ошибка воспроизведения голосового сообщения: {e}")
                self._greeting_played = True  # Помечаем как воспроизведенное чтобы не зависнуть
        
        # Переход в WAITING через 10 секунд
        if elapsed >= 10.0 and not hasattr(self, '_waiting_delay_start'):
            self.logger.info("=== 10 секунд прошло, ожидание 5 секунд перед возвратом в WAITING ===")
            self._waiting_delay_start = time.time()
        
        # Возврат в WAITING через 5 секунд после завершения доставки
        if hasattr(self, '_waiting_delay_start'):
            delay_elapsed = time.time() - self._waiting_delay_start
            if delay_elapsed >= 5.0:
                # Очистка флагов
                delattr(self, '_delivery_started')
                delattr(self, '_delivery_start_time')
                delattr(self, '_greeting_played')
                delattr(self, '_last_log_time')
                delattr(self, '_waiting_delay_start')
                if hasattr(self, '_delivering_debug_logged'):
                    delattr(self, '_delivering_debug_logged')
                
                self.logger.info("Доставка завершена, возврат в режим ожидания")
                self.transition_to(State.WAITING)
    
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
