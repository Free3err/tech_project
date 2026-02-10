import cv2
import json
import logging
import threading
import os
from typing import Optional, Callable, Tuple
from playsound3 import playsound
from db.functions import check_order
import serialConnection

logger = logging.getLogger(__name__)

# Headless режим для систем без дисплея
HEADLESS_MODE = (
    os.environ.get('HEADLESS') == '1' or 
    os.environ.get('QT_QPA_PLATFORM') == 'offscreen' or
    os.environ.get('DISPLAY') is None
)
if HEADLESS_MODE:
    logger.info("Запуск в headless режиме (без GUI)")


def qr_scanner():
    """
    Оригинальная функция сканирования QR кодов (для обратной совместимости)
    
    Сканирует QR коды с камеры, проверяет заказы и воспроизводит звуки
    """
    cap = cv2.VideoCapture(0)
    detector = cv2.QRCodeDetector()

    last_data = None

    while True:
        ret, frame = cap.read()
        data, bbox, _ = detector.detectAndDecode(frame)

        if bbox is not None:
            for i in range(len(bbox)):
                pt1 = tuple(map(int, bbox[i][0]))
                pt2 = tuple(map(int, bbox[(i + 1) % len(bbox)][0]))
                cv2.line(frame, pt1, pt2, color=(255, 0, 0), thickness=2)

            if data:
                cv2.putText(frame, data, (int(bbox[0][0][0]), int(bbox[0][0][1]) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                if data != last_data:
                    last_data = data
                    if check_order(data):
                        playsound('assets/successScan.wav')
                        serialConnection.ser.write(b"SUCCESS_SCAN\n")
                    else:
                        playsound("assets/failureScan.wav")
                        serialConnection.ser.write(b"FAILURE_SCAN\n")

        cv2.imshow("QR Scanner", frame)
        if cv2.waitKey(10) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


class OrderVerificationSystem:
    """
    Система проверки заказов для интеграции с машиной состояний
    
    Обеспечивает неблокирующее сканирование QR кодов с механизмом обратного вызова
    для уведомления машины состояний о результатах сканирования.
    """
    
    def __init__(self, db_session=None, serial_comm=None):
        """
        Инициализация системы проверки заказов
        
        Args:
            db_session: Сессия базы данных (опционально, использует глобальную если None)
            serial_comm: Связь с Arduino для LED эффектов (опционально)
        """
        self.db_session = db_session
        self.serial_comm = serial_comm
        self.cap = None
        self.detector = cv2.QRCodeDetector()
        self.scanning = False
        self.scan_thread = None
        self.callback = None
        self.last_data = None
        
    def start_scanning(self, callback: Callable[[bool, Optional[int]], None]) -> None:
        """
        Начать сканирование QR кода в отдельном потоке
        
        Args:
            callback: Функция обратного вызова (успех: bool, order_id: Optional[int])
                     Вызывается когда QR код обнаружен и проверен
        """
        if self.scanning:
            logger.warning("Сканирование уже запущено")
            return
            
        logger.info("Запуск сканирования QR кода")
        self.callback = callback
        self.scanning = True
        self.last_data = None
        
        # Запуск сканирования в отдельном потоке
        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()
        
    def stop_scanning(self) -> None:
        """
        Остановить сканирование и освободить камеру
        """
        logger.info("Остановка сканирования QR кода")
        self.scanning = False
        
        if self.scan_thread is not None and self.scan_thread != threading.current_thread():
            self.scan_thread.join(timeout=2.0)
            self.scan_thread = None
            
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            
        cv2.destroyAllWindows()
        
    def verify_order(self, order_data: str) -> Tuple[bool, Optional[int]]:
        """
        Проверка заказа по данным QR кода
        
        Args:
            order_data: JSON строка с данными заказа (order_id, secret_key)
            
        Returns:
            Кортеж (валидность: bool, order_id: Optional[int])
        """
        try:
            logger.debug(f"Проверка заказа: {order_data[:50]}...")  # Логируем первые 50 символов
            json_data = json.loads(order_data)
            order_id = json_data.get('order_id')
            secret_key = json_data.get('secret_key')
            
            if order_id is None or secret_key is None:
                logger.warning("QR код не содержит order_id или secret_key")
                return (False, None)
            
            # Используем существующую функцию check_order
            is_valid = check_order(order_data)
            
            if is_valid:
                logger.info(f"Заказ {order_id} успешно проверен")
                return (True, order_id)
            else:
                logger.warning(f"Заказ {order_id} не прошел проверку")
                return (False, order_id)
                
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Ошибка парсинга QR кода: {e}")
            return (False, None)
            
    def _scan_loop(self) -> None:
        """
        Внутренний цикл сканирования (выполняется в отдельном потоке)
        """
        try:
            logger.debug("Инициализация камеры для сканирования QR кода")
            self.cap = cv2.VideoCapture(0)
            
            if not self.cap.isOpened():
                logger.error("Не удалось открыть камеру")
                if self.callback:
                    self.callback(False, None)
                return
            
            logger.info("Камера инициализирована, начало сканирования")
                
            while self.scanning:
                ret, frame = self.cap.read()
                
                if not ret:
                    continue
                    
                data, bbox, _ = self.detector.detectAndDecode(frame)
                
                # Отображение рамки вокруг QR кода
                if bbox is not None:
                    for i in range(len(bbox)):
                        pt1 = tuple(map(int, bbox[i][0]))
                        pt2 = tuple(map(int, bbox[(i + 1) % len(bbox)][0]))
                        cv2.line(frame, pt1, pt2, color=(255, 0, 0), thickness=2)
                        
                    if data and data != self.last_data:
                        self.last_data = data
                        logger.info(f"QR код обнаружен")
                        
                        # Проверка заказа
                        is_valid, order_id = self.verify_order(data)
                        
                        # Отправка LED команд если доступна связь
                        if self.serial_comm:
                            if is_valid:
                                logger.debug("Отправка команды SUCCESS_SCAN")
                                self.serial_comm.write(b"SUCCESS_SCAN\n")
                            else:
                                logger.debug("Отправка команды FAILURE_SCAN")
                                self.serial_comm.write(b"FAILURE_SCAN\n")
                        elif serialConnection.ser:
                            # Fallback на глобальную связь
                            if is_valid:
                                logger.debug("Отправка команды SUCCESS_SCAN (fallback)")
                                serialConnection.ser.write(b"SUCCESS_SCAN\n")
                            else:
                                logger.debug("Отправка команды FAILURE_SCAN (fallback)")
                                serialConnection.ser.write(b"FAILURE_SCAN\n")
                        
                        # Вызов callback с результатом
                        if self.callback:
                            logger.info(f"Вызов callback с результатом: valid={is_valid}, order_id={order_id}")
                            self.callback(is_valid, order_id)
                            
                        # Остановка сканирования после первого результата
                        self.scanning = False
                        break
                        
                # Отображение окна только если не headless режим
                if not HEADLESS_MODE:
                    cv2.imshow("QR Scanner", frame)
                    if cv2.waitKey(10) & 0xFF == 27:  # ESC для выхода
                        logger.info("Сканирование прервано пользователем (ESC)")
                        self.scanning = False
                        break
                else:
                    # В headless режиме просто небольшая задержка
                    cv2.waitKey(10)
                    
        except Exception as e:
            logger.error(f"Ошибка сканирования: {e}", exc_info=True)
            if self.callback:
                self.callback(False, None)
        finally:
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            if not HEADLESS_MODE:
                cv2.destroyAllWindows()
            logger.debug("Камера освобождена")
