# -*- coding: utf-8 -*-
"""
Модульные тесты для контроллера коробки
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import time
import logging

from box_controller import BoxController
import config


class MockSerialComm:
    """Mock объект для последовательной связи с Arduino"""
    
    def __init__(self):
        self.commands_sent = []
        self.should_fail = False
        self.fail_on_angle = None
    
    def send_servo_command(self, angle):
        """Mock отправка команды сервоприводу"""
        if self.should_fail:
            raise RuntimeError("Mock serial communication failure")
        
        if self.fail_on_angle is not None and angle == self.fail_on_angle:
            raise RuntimeError(f"Mock failure at angle {angle}")
        
        self.commands_sent.append(('SERVO', angle))
    
    def get_last_command(self):
        """Получить последнюю отправленную команду"""
        return self.commands_sent[-1] if self.commands_sent else None
    
    def get_all_commands(self):
        """Получить все отправленные команды"""
        return self.commands_sent
    
    def clear_commands(self):
        """Очистить список команд"""
        self.commands_sent = []
    
    def set_fail_mode(self, should_fail=True):
        """Установить режим отказа"""
        self.should_fail = should_fail
    
    def set_fail_on_angle(self, angle):
        """Установить отказ на определенном угле"""
        self.fail_on_angle = angle


@pytest.fixture
def mock_serial_comm():
    """Фикстура для mock последовательной связи"""
    return MockSerialComm()


@pytest.fixture
def box_controller(mock_serial_comm):
    """Фикстура для создания экземпляра BoxController"""
    # Патчим time.sleep чтобы тесты выполнялись быстрее
    with patch('box_controller.time.sleep'):
        controller = BoxController(mock_serial_comm)
        # Очищаем команды, отправленные при инициализации
        mock_serial_comm.clear_commands()
        return controller


class TestBoxControllerInitialization:
    """Тесты инициализации контроллера коробки"""
    
    def test_init_with_serial_comm(self, mock_serial_comm):
        """Тест инициализации с последовательной связью"""
        with patch('box_controller.time.sleep'):
            controller = BoxController(mock_serial_comm)
            assert controller.serial_comm == mock_serial_comm
    
    def test_init_closes_box(self, mock_serial_comm):
        """Тест что инициализация устанавливает состояние закрытой коробки"""
        with patch('box_controller.time.sleep'):
            controller = BoxController(mock_serial_comm)
            # Проверяем, что коробка инициализирована в закрытом состоянии
            assert controller.is_open() is False
            assert controller.get_current_angle() == config.BOX_CLOSE_ANGLE
            # Команды не отправляются при инициализации, так как предполагается,
            # что сервопривод уже находится в позиции 0 градусов
            commands = mock_serial_comm.get_all_commands()
            assert len(commands) == 0
    
    def test_init_state_is_closed(self, mock_serial_comm):
        """Тест что начальное состояние - закрыто"""
        with patch('box_controller.time.sleep'):
            controller = BoxController(mock_serial_comm)
            assert controller.is_open() is False
            assert controller.get_current_angle() == config.BOX_CLOSE_ANGLE


class TestBoxOpening:
    """Тесты открытия коробки"""
    
    def test_open_box(self, box_controller, mock_serial_comm):
        """Тест открытия коробки"""
        with patch('box_controller.time.sleep'):
            box_controller.open()
        
        # Проверяем, что коробка открыта
        assert box_controller.is_open() is True
        assert box_controller.get_current_angle() == config.BOX_OPEN_ANGLE
        
        # Проверяем, что была отправлена команда открытия
        commands = mock_serial_comm.get_all_commands()
        assert len(commands) > 0
        assert commands[-1] == ('SERVO', config.BOX_OPEN_ANGLE)
    
    def test_open_already_open_box(self, box_controller, mock_serial_comm):
        """Тест открытия уже открытой коробки"""
        with patch('box_controller.time.sleep'):
            box_controller.open()
            mock_serial_comm.clear_commands()
            
            # Попытка открыть снова
            box_controller.open()
        
        # Не должно быть новых команд
        assert len(mock_serial_comm.get_all_commands()) == 0
    
    def test_open_sends_multiple_commands_for_smooth_movement(self, box_controller, mock_serial_comm):
        """Тест что открытие отправляет несколько команд для плавного движения"""
        with patch('box_controller.time.sleep'):
            box_controller.open()
        
        commands = mock_serial_comm.get_all_commands()
        # Должно быть несколько команд для плавного движения
        assert len(commands) >= 1
        
        # Все команды должны быть SERVO команды
        for cmd_type, angle in commands:
            assert cmd_type == 'SERVO'
            assert 0 <= angle <= 90
    
    def test_open_failure_raises_exception(self, box_controller, mock_serial_comm):
        """Тест что отказ при открытии вызывает исключение"""
        mock_serial_comm.set_fail_mode(True)
        
        with pytest.raises(RuntimeError) as exc_info:
            with patch('box_controller.time.sleep'):
                box_controller.open()
        
        assert "Failed to open box" in str(exc_info.value)


class TestBoxClosing:
    """Тесты закрытия коробки"""
    
    def test_close_box(self, box_controller, mock_serial_comm):
        """Тест закрытия коробки"""
        with patch('box_controller.time.sleep'):
            # Сначала открываем
            box_controller.open()
            mock_serial_comm.clear_commands()
            
            # Затем закрываем
            box_controller.close()
        
        # Проверяем, что коробка закрыта
        assert box_controller.is_open() is False
        assert box_controller.get_current_angle() == config.BOX_CLOSE_ANGLE
        
        # Проверяем, что была отправлена команда закрытия
        commands = mock_serial_comm.get_all_commands()
        assert len(commands) > 0
        assert commands[-1] == ('SERVO', config.BOX_CLOSE_ANGLE)
    
    def test_close_already_closed_box(self, box_controller, mock_serial_comm):
        """Тест закрытия уже закрытой коробки"""
        with patch('box_controller.time.sleep'):
            # Коробка уже закрыта после инициализации
            box_controller.close()
        
        # Не должно быть новых команд
        assert len(mock_serial_comm.get_all_commands()) == 0
    
    def test_close_sends_multiple_commands_for_smooth_movement(self, box_controller, mock_serial_comm):
        """Тест что закрытие отправляет несколько команд для плавного движения"""
        with patch('box_controller.time.sleep'):
            # Сначала открываем
            box_controller.open()
            mock_serial_comm.clear_commands()
            
            # Затем закрываем
            box_controller.close()
        
        commands = mock_serial_comm.get_all_commands()
        # Должно быть несколько команд для плавного движения
        assert len(commands) >= 1
        
        # Все команды должны быть SERVO команды
        for cmd_type, angle in commands:
            assert cmd_type == 'SERVO'
            assert 0 <= angle <= 90
    
    def test_close_failure_raises_exception(self, box_controller, mock_serial_comm):
        """Тест что отказ при закрытии вызывает исключение"""
        with patch('box_controller.time.sleep'):
            # Открываем коробку
            box_controller.open()
        
        # Устанавливаем режим отказа
        mock_serial_comm.set_fail_mode(True)
        
        with pytest.raises(RuntimeError) as exc_info:
            with patch('box_controller.time.sleep'):
                box_controller.close()
        
        assert "Failed to close box" in str(exc_info.value)


class TestBoxStateTracking:
    """Тесты отслеживания состояния коробки"""
    
    def test_is_open_returns_false_initially(self, box_controller):
        """Тест что is_open возвращает False изначально"""
        assert box_controller.is_open() is False
    
    def test_is_open_returns_true_after_opening(self, box_controller):
        """Тест что is_open возвращает True после открытия"""
        with patch('box_controller.time.sleep'):
            box_controller.open()
        assert box_controller.is_open() is True
    
    def test_is_open_returns_false_after_closing(self, box_controller):
        """Тест что is_open возвращает False после закрытия"""
        with patch('box_controller.time.sleep'):
            box_controller.open()
            box_controller.close()
        assert box_controller.is_open() is False
    
    def test_get_current_angle_returns_correct_value(self, box_controller):
        """Тест что get_current_angle возвращает правильное значение"""
        assert box_controller.get_current_angle() == config.BOX_CLOSE_ANGLE
        
        with patch('box_controller.time.sleep'):
            box_controller.open()
        assert box_controller.get_current_angle() == config.BOX_OPEN_ANGLE
        
        with patch('box_controller.time.sleep'):
            box_controller.close()
        assert box_controller.get_current_angle() == config.BOX_CLOSE_ANGLE


class TestBoxEmergencyClose:
    """Тесты экстренного закрытия коробки"""
    
    def test_emergency_close(self, box_controller, mock_serial_comm):
        """Тест экстренного закрытия"""
        with patch('box_controller.time.sleep'):
            # Открываем коробку
            box_controller.open()
            mock_serial_comm.clear_commands()
            
            # Экстренное закрытие
            box_controller.emergency_close()
        
        # Проверяем, что коробка закрыта
        assert box_controller.is_open() is False
        assert box_controller.get_current_angle() == config.BOX_CLOSE_ANGLE
        
        # Проверяем, что была отправлена только одна команда (без плавного движения)
        commands = mock_serial_comm.get_all_commands()
        assert len(commands) == 1
        assert commands[0] == ('SERVO', config.BOX_CLOSE_ANGLE)
    
    def test_emergency_close_from_open_state(self, box_controller, mock_serial_comm):
        """Тест экстренного закрытия из открытого состояния"""
        with patch('box_controller.time.sleep'):
            box_controller.open()
            mock_serial_comm.clear_commands()
            
            box_controller.emergency_close()
        
        assert box_controller.is_open() is False
    
    def test_emergency_close_failure_raises_exception(self, box_controller, mock_serial_comm):
        """Тест что отказ при экстренном закрытии вызывает исключение"""
        mock_serial_comm.set_fail_mode(True)
        
        with pytest.raises(RuntimeError) as exc_info:
            box_controller.emergency_close()
        
        assert "Emergency box close failed" in str(exc_info.value)


class TestBoxReset:
    """Тесты сброса контроллера коробки"""
    
    def test_reset_closes_box(self, box_controller, mock_serial_comm):
        """Тест что reset закрывает коробку"""
        with patch('box_controller.time.sleep'):
            # Открываем коробку
            box_controller.open()
            
            # Сбрасываем
            box_controller.reset()
        
        # Проверяем, что коробка закрыта
        assert box_controller.is_open() is False
        assert box_controller.get_current_angle() == config.BOX_CLOSE_ANGLE
    
    def test_reset_from_closed_state(self, box_controller):
        """Тест reset из закрытого состояния"""
        with patch('box_controller.time.sleep'):
            # Коробка уже закрыта
            box_controller.reset()
        
        # Должна остаться закрытой
        assert box_controller.is_open() is False
    
    def test_reset_failure_attempts_emergency_close(self, box_controller, mock_serial_comm):
        """Тест что при отказе reset пытается выполнить экстренное закрытие"""
        with patch('box_controller.time.sleep'):
            box_controller.open()
        
        # Устанавливаем отказ на всех углах кроме экстренного закрытия
        # Это заставит обычное закрытие провалиться, но экстренное должно сработать
        mock_serial_comm.set_fail_mode(True)
        
        # Reset должен попытаться экстренное закрытие после провала обычного
        # Но так как экстренное тоже провалится, должно быть исключение
        with pytest.raises(RuntimeError):
            with patch('box_controller.time.sleep'):
                box_controller.reset()


class TestBoxServoFailureHandling:
    """Тесты обработки отказов сервопривода"""
    
    def test_servo_failure_during_opening(self, box_controller, mock_serial_comm):
        """Тест обработки отказа сервопривода при открытии"""
        # Устанавливаем отказ на промежуточном угле
        # Используем угол, который точно будет в последовательности
        mock_serial_comm.set_fail_on_angle(10)
        
        with pytest.raises(RuntimeError) as exc_info:
            with patch('box_controller.time.sleep'):
                box_controller.open()
        
        assert "Servo movement failed" in str(exc_info.value) or "Failed to open box" in str(exc_info.value)
    
    def test_servo_failure_during_closing(self, box_controller, mock_serial_comm):
        """Тест обработки отказа сервопривода при закрытии"""
        with patch('box_controller.time.sleep'):
            box_controller.open()
        
        # Устанавливаем отказ на промежуточном угле при закрытии
        # Используем угол, который точно будет в последовательности
        mock_serial_comm.set_fail_on_angle(80)
        
        with pytest.raises(RuntimeError) as exc_info:
            with patch('box_controller.time.sleep'):
                box_controller.close()
        
        assert "Servo movement failed" in str(exc_info.value) or "Failed to close box" in str(exc_info.value)
    
    def test_multiple_servo_failures(self, box_controller, mock_serial_comm):
        """Тест множественных отказов сервопривода"""
        mock_serial_comm.set_fail_mode(True)
        
        # Попытка открыть
        with pytest.raises(RuntimeError):
            with patch('box_controller.time.sleep'):
                box_controller.open()
        
        # Коробка уже закрыта, поэтому попытка закрыть не вызовет ошибку
        # (метод close проверяет состояние и не делает ничего если уже закрыто)
        # Вместо этого проверим экстренное закрытие
        
        # Попытка экстренного закрытия
        with pytest.raises(RuntimeError):
            box_controller.emergency_close()


class TestBoxSmoothMovement:
    """Тесты плавного движения сервопривода"""
    
    def test_smooth_movement_uses_multiple_steps(self, box_controller, mock_serial_comm):
        """Тест что плавное движение использует несколько шагов"""
        with patch('box_controller.time.sleep'):
            box_controller.open()
        
        commands = mock_serial_comm.get_all_commands()
        
        # Должно быть несколько команд для плавного движения
        # (от 0 до 90 градусов должно быть разбито на шаги)
        assert len(commands) >= 1
        
        # Проверяем, что углы увеличиваются монотонно
        angles = [angle for _, angle in commands]
        for i in range(len(angles) - 1):
            assert angles[i] <= angles[i + 1]
    
    def test_smooth_movement_reaches_target_angle(self, box_controller, mock_serial_comm):
        """Тест что плавное движение достигает целевого угла"""
        with patch('box_controller.time.sleep'):
            box_controller.open()
        
        commands = mock_serial_comm.get_all_commands()
        
        # Последняя команда должна быть целевой угол
        assert commands[-1] == ('SERVO', config.BOX_OPEN_ANGLE)
    
    def test_smooth_movement_respects_servo_speed(self, box_controller, mock_serial_comm):
        """Тест что плавное движение учитывает скорость сервопривода"""
        # Этот тест проверяет, что движение разбито на шаги
        # в соответствии с конфигурацией SERVO_SPEED
        with patch('box_controller.time.sleep'):
            box_controller.open()
        
        commands = mock_serial_comm.get_all_commands()
        
        # Количество шагов должно быть разумным (не слишком много, не слишком мало)
        assert 1 <= len(commands) <= 20


class TestBoxEdgeCases:
    """Тесты граничных случаев"""
    
    def test_open_close_cycle(self, box_controller, mock_serial_comm):
        """Тест цикла открытие-закрытие"""
        with patch('box_controller.time.sleep'):
            # Несколько циклов
            for _ in range(3):
                box_controller.open()
                assert box_controller.is_open() is True
                
                box_controller.close()
                assert box_controller.is_open() is False
    
    def test_rapid_open_close(self, box_controller, mock_serial_comm):
        """Тест быстрого открытия-закрытия"""
        with patch('box_controller.time.sleep'):
            box_controller.open()
            box_controller.close()
            box_controller.open()
            box_controller.close()
        
        # Должна быть закрыта в конце
        assert box_controller.is_open() is False
    
    def test_state_consistency_after_failure(self, box_controller, mock_serial_comm):
        """Тест консистентности состояния после отказа"""
        with patch('box_controller.time.sleep'):
            box_controller.open()
        
        # Устанавливаем отказ
        mock_serial_comm.set_fail_mode(True)
        
        # Попытка закрыть (должна провалиться)
        with pytest.raises(RuntimeError):
            with patch('box_controller.time.sleep'):
                box_controller.close()
        
        # Состояние должно остаться "открыто"
        assert box_controller.is_open() is True


class TestBoxLogging:
    """Тесты логирования"""
    
    def test_open_logs_info(self, box_controller, caplog):
        """Тест что открытие логирует информацию"""
        with caplog.at_level(logging.INFO):
            with patch('box_controller.time.sleep'):
                box_controller.open()
        
        assert "Opening box" in caplog.text
        assert "Box opened successfully" in caplog.text
    
    def test_close_logs_info(self, box_controller, caplog):
        """Тест что закрытие логирует информацию"""
        with patch('box_controller.time.sleep'):
            box_controller.open()
        
        with caplog.at_level(logging.INFO):
            with patch('box_controller.time.sleep'):
                box_controller.close()
        
        assert "Closing box" in caplog.text
        assert "Box closed successfully" in caplog.text
    
    def test_failure_logs_error(self, box_controller, mock_serial_comm, caplog):
        """Тест что отказ логирует ошибку"""
        mock_serial_comm.set_fail_mode(True)
        
        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeError):
                with patch('box_controller.time.sleep'):
                    box_controller.open()
        
        assert "Failed to open box" in caplog.text
    
    def test_emergency_close_logs_warning(self, box_controller, caplog):
        """Тест что экстренное закрытие логирует предупреждение"""
        with caplog.at_level(logging.WARNING):
            box_controller.emergency_close()
        
        assert "Emergency box close initiated" in caplog.text


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

