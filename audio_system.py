# -*- coding: utf-8 -*-
"""
Аудио система для RelayBot
Обеспечивает голосовую и звуковую обратную связь для взаимодействия с клиентами и персоналом склада
"""

import os
import logging
from typing import Optional
import threading
from playsound3 import playsound

import config


class AudioSystem:
    """
    Класс для управления аудио обратной связью робота
    
    Обеспечивает воспроизведение голосовых подсказок и звуковых эффектов
    для взаимодействия с клиентами и персоналом склада.
    """
    
    def __init__(self, audio_dir: str = None):
        """
        Инициализация аудио системы
        
        Args:
            audio_dir: Директория с аудио файлами (по умолчанию из config.AUDIO_DIR)
        """
        self.audio_dir = audio_dir if audio_dir is not None else config.AUDIO_DIR
        self.logger = logging.getLogger(__name__)
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_playback = False
        
        # Проверка существования директории с аудио файлами
        if not os.path.exists(self.audio_dir):
            self.logger.warning(f"Директория аудио файлов не найдена: {self.audio_dir}")
            os.makedirs(self.audio_dir, exist_ok=True)
            self.logger.info(f"Создана директория: {self.audio_dir}")
        
        self.logger.info(f"Аудио система инициализирована. Директория: {self.audio_dir}")
    
    def _get_audio_path(self, audio_file: str) -> str:
        """
        Получить полный путь к аудио файлу
        
        Args:
            audio_file: Имя аудио файла
            
        Returns:
            Полный путь к файлу
        """
        return os.path.join(self.audio_dir, audio_file)
    
    def _check_audio_file(self, audio_file: str) -> bool:
        """
        Проверить существование аудио файла
        
        Args:
            audio_file: Имя аудио файла
            
        Returns:
            True если файл существует, False иначе
        """
        audio_path = self._get_audio_path(audio_file)
        exists = os.path.exists(audio_path)
        
        if not exists:
            self.logger.warning(f"Аудио файл не найден: {audio_path}")
        
        return exists
    
    def play(self, audio_file: str, blocking: bool = False) -> None:
        """
        Воспроизвести аудио файл
        
        Args:
            audio_file: Имя файла для воспроизведения
            blocking: Если True, ждать завершения воспроизведения
        """
        audio_path = self._get_audio_path(audio_file)
        
        # Проверка существования файла
        if not self._check_audio_file(audio_file):
            self.logger.error(f"Невозможно воспроизвести файл: {audio_file}")
            return
        
        self.logger.info(f"Воспроизведение аудио: {audio_file} (blocking={blocking})")
        
        try:
            if blocking:
                # Блокирующее воспроизведение
                playsound(audio_path, block=True)
            else:
                # Неблокирующее воспроизведение в отдельном потоке
                self._stop_playback = False
                self._playback_thread = threading.Thread(
                    target=self._play_in_thread,
                    args=(audio_path,),
                    daemon=True
                )
                self._playback_thread.start()
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения аудио {audio_file}: {e}")
    
    def _play_in_thread(self, audio_path: str) -> None:
        """
        Воспроизвести аудио в отдельном потоке
        
        Args:
            audio_path: Полный путь к аудио файлу
        """
        try:
            if not self._stop_playback:
                playsound(audio_path, block=True)
        except Exception as e:
            self.logger.error(f"Ошибка воспроизведения в потоке: {e}")
    
    def stop(self) -> None:
        """
        Остановить текущее воспроизведение
        
        Примечание: playsound3 не поддерживает прямую остановку воспроизведения.
        Этот метод устанавливает флаг для предотвращения нового воспроизведения.
        """
        self.logger.info("Остановка воспроизведения аудио")
        self._stop_playback = True
        
        # Ожидание завершения потока воспроизведения
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=1.0)
    
    def request_qr_code(self) -> None:
        """
        Запросить QR код у клиента
        
        Воспроизводит: "Пожалуйста, покажите QR код вашего заказа"
        """
        self.logger.info("Запрос QR кода у клиента")
        self.play(config.AUDIO_REQUEST_QR, blocking=False)
    
    def announce_order_accepted(self) -> None:
        """
        Объявить принятие заказа
        
        Воспроизводит: "Заказ принят. Еду на склад."
        """
        self.logger.info("Объявление принятия заказа")
        self.play(config.AUDIO_ORDER_ACCEPTED, blocking=False)
    
    def announce_order_rejected(self) -> None:
        """
        Объявить отклонение заказа
        
        Воспроизводит: "Заказ не найден. Пожалуйста, проверьте QR код."
        """
        self.logger.info("Объявление отклонения заказа")
        self.play(config.AUDIO_ORDER_REJECTED, blocking=False)
    
    def announce_order_number(self, order_id: int) -> None:
        """
        Объявить номер заказа на складе
        
        Args:
            order_id: Номер заказа
            
        Воспроизводит: "Заказ номер <order_id>"
        """
        self.logger.info(f"Объявление номера заказа: {order_id}")
        
        # Попытка воспроизвести специфичный файл для номера заказа
        order_audio_file = f"order_{order_id}.wav"
        
        if self._check_audio_file(order_audio_file):
            self.play(order_audio_file, blocking=False)
        else:
            # Если специфичный файл не найден, используем общий файл
            # (в будущем можно добавить синтез речи)
            self.logger.warning(f"Специфичный аудио файл для заказа {order_id} не найден")
            # Можно добавить воспроизведение общего файла "order_number.wav"
            # и затем цифры, если такие файлы будут созданы
    
    def greet_delivery(self) -> None:
        """
        Приветствие при доставке
        
        Воспроизводит: "Ваш заказ доставлен. Приятного дня!"
        """
        self.logger.info("Приветствие при доставке")
        self.play(config.AUDIO_DELIVERY_GREETING, blocking=False)
    
    def play_success_sound(self) -> None:
        """
        Воспроизвести звук успеха
        
        Используется при успешном сканировании QR кода
        """
        self.logger.info("Воспроизведение звука успеха")
        # Используем существующий файл из корневой директории assets
        success_path = os.path.join('assets', config.AUDIO_SUCCESS_SCAN)
        if os.path.exists(success_path):
            try:
                playsound(success_path, block=False)
            except Exception as e:
                self.logger.error(f"Ошибка воспроизведения звука успеха: {e}")
        else:
            self.logger.warning(f"Файл звука успеха не найден: {success_path}")
    
    def play_failure_sound(self) -> None:
        """
        Воспроизвести звук неудачи
        
        Используется при неудачном сканировании QR кода
        """
        self.logger.info("Воспроизведение звука неудачи")
        # Используем существующий файл из корневой директории assets
        failure_path = os.path.join('assets', config.AUDIO_FAILURE_SCAN)
        if os.path.exists(failure_path):
            try:
                playsound(failure_path, block=False)
            except Exception as e:
                self.logger.error(f"Ошибка воспроизведения звука неудачи: {e}")
        else:
            self.logger.warning(f"Файл звука неудачи не найден: {failure_path}")
    
    def play_error_sound(self) -> None:
        """
        Воспроизвести звук ошибки
        
        Используется при возникновении ошибок в системе
        """
        self.logger.info("Воспроизведение звука ошибки")
        self.play(config.AUDIO_ERROR, blocking=False)
    
    def announce_loading_complete(self) -> None:
        """
        Объявить окончание загрузки
        
        Воспроизводит: "Загрузка завершена"
        """
        self.logger.info("Объявление окончания загрузки")
        self.play("loading_complete.wav", blocking=False)
    
    def request_voice_code(self) -> None:
        """
        Запросить голосовой код
        
        Воспроизводит: "Пожалуйста, продиктуйте код из приложения"
        """
        self.logger.info("Запрос голосового кода")
        self.play("request_voice_code.wav", blocking=False)
    
    def announce_code_accepted(self) -> None:
        """
        Объявить принятие кода
        
        Воспроизводит: "Код принят"
        """
        self.logger.info("Объявление принятия кода")
        self.play("code_accepted.wav", blocking=False)
    
    def announce_code_rejected(self) -> None:
        """
        Объявить отклонение кода
        
        Воспроизводит: "Код неверный, попробуйте еще раз"
        """
        self.logger.info("Объявление отклонения кода")
        self.play("code_rejected.wav", blocking=False)


# Пример использования
if __name__ == "__main__":
    # Настройка логирования для тестирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Создание экземпляра аудио системы
    audio = AudioSystem()
    
    print("Тестирование аудио системы...")
    print("1. Запрос QR кода")
    audio.request_qr_code()
    
    import time
    time.sleep(2)
    
    print("2. Объявление принятия заказа")
    audio.announce_order_accepted()
    
    time.sleep(2)
    
    print("3. Объявление номера заказа")
    audio.announce_order_number(42)
    
    time.sleep(2)
    
    print("4. Приветствие при доставке")
    audio.greet_delivery()
    
    time.sleep(2)
    
    print("5. Звук успеха")
    audio.play_success_sound()
    
    time.sleep(2)
    
    print("6. Звук неудачи")
    audio.play_failure_sound()
    
    print("\nТестирование завершено!")

