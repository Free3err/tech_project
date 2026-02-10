# -*- coding: utf-8 -*-
"""
Контроллер механизма коробки для RelayBot
Управляет сервоприводом для открытия/закрытия отсека для посылок
"""

import time
import logging
from typing import Optional
import config

logger = logging.getLogger(__name__)


class BoxController:
    """
    Контроллер коробки для управления сервоприводом отсека посылок
    
    Управляет открытием и закрытием коробки через последовательную связь с Arduino.
    Отслеживает текущее состояние коробки и обеспечивает плавное движение сервопривода.
    """
    
    def __init__(self, serial_comm):
        """
        Инициализация контроллера коробки
        
        Args:
            serial_comm: Модуль последовательной связи с Arduino (serialConnection)
        """
        self.serial_comm = serial_comm
        self._is_open = False
        self._current_angle = config.BOX_CLOSE_ANGLE_2
        self._target_angle = config.BOX_CLOSE_ANGLE_2
        
        logger.info("BoxController initialized")
        # Не отправляем команду серво при инициализации - серво остается на своем месте
    
    def open(self) -> None:
        """
        Открыть коробку (90 градусов)
        
        Отправляет команду сервоприводу для открытия коробки до угла BOX_OPEN_ANGLE.
        Движение выполняется плавно для предотвращения повреждения посылки.
        
        Raises:
            RuntimeError: Если не удалось отправить команду сервоприводу
        """
        if self._is_open:
            logger.debug("Box is already open")
            return
        
        logger.info("Opening box")
        
        try:
            # Плавное открытие коробки
            self._move_to_angle(config.BOX_OPEN_ANGLE)
            self._is_open = True
            logger.info("Box opened successfully")
            
        except Exception as e:
            logger.error(f"Failed to open box: {e}")
            raise RuntimeError(f"Failed to open box: {e}")
    
    def close(self) -> None:
        """
        Закрыть коробку (0 градусов)
        
        Отправляет команду сервоприводу для закрытия коробки до угла BOX_CLOSE_ANGLE_2.
        Движение выполняется плавно для предотвращения повреждения посылки.
        
        Raises:
            RuntimeError: Если не удалось отправить команду сервоприводу
        """
        if not self._is_open and self._current_angle == config.BOX_CLOSE_ANGLE_2:
            logger.debug("Box is already closed")
            return
        
        logger.info("Closing box")
        
        try:
            # Плавное закрытие коробки
            self._move_to_angle(config.BOX_CLOSE_ANGLE_2)
            self._is_open = False
            logger.info("Box closed successfully")
            
        except Exception as e:
            logger.error(f"Failed to close box: {e}")
            raise RuntimeError(f"Failed to close box: {e}")
    
    def is_open(self) -> bool:
        """
        Проверить, открыта ли коробка
        
        Returns:
            True если коробка открыта, False если закрыта
        """
        return self._is_open
    
    def get_current_angle(self) -> int:
        """
        Получить текущий угол сервопривода
        
        Returns:
            Текущий угол в градусах (0-90)
        """
        return self._current_angle
    
    def _move_to_angle(self, target_angle: int) -> None:
        """
        Переместить сервопривод к целевому углу
        
        Args:
            target_angle: Целевой угол (0-180 градусов)
        
        Raises:
            ValueError: Если угол вне допустимого диапазона
            RuntimeError: Если не удалось отправить команду
        """
        if not (0 <= target_angle <= 180):
            raise ValueError(f"Target angle must be 0-180, got {target_angle}")
        
        logger.debug(f"Moving servo to {target_angle}°")
        
        # Отправить команду напрямую без плавного движения
        try:
            self.serial_comm.send_servo_command(target_angle)
            self._current_angle = target_angle
            self._target_angle = target_angle
        except Exception as e:
            logger.error(f"Failed to move servo to {target_angle}°: {e}")
            raise RuntimeError(f"Failed to move servo: {e}")
    
    def emergency_close(self) -> None:
        """
        Экстренное закрытие коробки без плавного движения
        
        Используется в аварийных ситуациях для быстрого закрытия коробки.
        Отправляет команду напрямую без промежуточных шагов.
        
        Raises:
            RuntimeError: Если не удалось отправить команду
        """
        logger.warning("Emergency box close initiated")
        
        try:
            self.serial_comm.send_servo_command(config.BOX_CLOSE_ANGLE_2)
            self._current_angle = config.BOX_CLOSE_ANGLE_2
            self._is_open = False
            logger.info("Emergency box close completed")
            
        except Exception as e:
            logger.error(f"Emergency box close failed: {e}")
            raise RuntimeError(f"Emergency box close failed: {e}")
    
    def reset(self) -> None:
        """
        Сброс контроллера коробки к начальному состоянию
        
        Закрывает коробку и сбрасывает внутреннее состояние.
        """
        logger.info("Resetting box controller")
        try:
            self.close()
        except Exception as e:
            logger.error(f"Failed to reset box controller: {e}")
            # Попытка экстренного закрытия
            try:
                self.emergency_close()
            except Exception as e2:
                logger.critical(f"Emergency close also failed during reset: {e2}")
                raise RuntimeError(f"Box controller reset failed: {e}, {e2}")
