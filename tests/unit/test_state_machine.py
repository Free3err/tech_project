# -*- coding: utf-8 -*-
"""
Модульные тесты для машины состояний RelayBot
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import time

from state_machine import StateMachine, State
from navigation import Position, StateContext


class TestStateMachineInitialization:
    """Тесты инициализации машины состояний"""
    
    def test_state_machine_initializes_in_waiting_state(self):
        """Тест: машина состояний инициализируется в состоянии WAITING"""
        # Arrange
        navigation = Mock()
        audio = Mock()
        order_verifier = Mock()
        serial_comm = Mock()
        lidar = Mock()
        box_controller = Mock()
        
        # Act
        sm = StateMachine(navigation, audio, order_verifier, serial_comm, lidar, box_controller)
        
        # Assert
        assert sm.current_state == State.WAITING
        assert sm.context.current_position.x == 0.0
        assert sm.context.current_position.y == 0.0
        assert sm.context.target_position is None
        assert sm.context.customer_position is None
        assert sm.context.current_order_id is None
        assert sm.recovery_attempts == 0
        assert sm.is_running == False
    
    def test_state_machine_stores_subsystem_references(self):
        """Тест: машина состояний сохраняет ссылки на подсистемы"""
        # Arrange
        navigation = Mock()
        audio = Mock()
        order_verifier = Mock()
        serial_comm = Mock()
        lidar = Mock()
        box_controller = Mock()
        
        # Act
        sm = StateMachine(navigation, audio, order_verifier, serial_comm, lidar, box_controller)
        
        # Assert
        assert sm.navigation is navigation
        assert sm.audio is audio
        assert sm.order_verifier is order_verifier
        assert sm.serial is serial_comm
        assert sm.lidar is lidar
        assert sm.box_controller is box_controller


class TestStateTransitions:
    """Тесты переходов между состояниями"""
    
    def test_transition_to_changes_state(self):
        """Тест: transition_to изменяет текущее состояние"""
        # Arrange
        sm = self._create_mock_state_machine()
        
        # Act
        sm.transition_to(State.APPROACHING)
        
        # Assert
        assert sm.current_state == State.APPROACHING
    
    def test_transition_to_sends_led_command(self):
        """Тест: transition_to отправляет LED команду"""
        # Arrange
        sm = self._create_mock_state_machine()
        
        # Act
        sm.transition_to(State.APPROACHING)
        
        # Assert
        sm.serial.send_led_command.assert_called_once_with("LED_MOVING")
    
    def test_transition_to_logs_state_change(self, caplog):
        """Тест: transition_to логирует изменение состояния"""
        # Arrange
        sm = self._create_mock_state_machine()
        
        # Act
        with caplog.at_level('INFO'):
            sm.transition_to(State.VERIFYING)
        
        # Assert
        assert "Переход состояния: WAITING -> VERIFYING" in caplog.text
    
    def _create_mock_state_machine(self):
        """Создание машины состояний с mock подсистемами"""
        navigation = Mock()
        audio = Mock()
        order_verifier = Mock()
        serial_comm = Mock()
        lidar = Mock()
        box_controller = Mock()
        
        return StateMachine(navigation, audio, order_verifier, serial_comm, lidar, box_controller)


class TestErrorHandling:
    """Тесты обработки ошибок"""
    
    def test_handle_error_transitions_to_error_recovery(self):
        """Тест: handle_error переходит в состояние ERROR_RECOVERY"""
        # Arrange
        sm = self._create_mock_state_machine()
        error = RuntimeError("Test error")
        
        # Act
        sm.handle_error(error)
        
        # Assert
        assert sm.current_state == State.ERROR_RECOVERY
        assert sm.context.error_message == "Test error"
        assert sm.recovery_attempts == 1
    
    def test_handle_error_increments_recovery_attempts(self):
        """Тест: handle_error увеличивает счетчик попыток восстановления"""
        # Arrange
        sm = self._create_mock_state_machine()
        
        # Act
        sm.handle_error(RuntimeError("Error 1"))
        sm.handle_error(RuntimeError("Error 2"))
        
        # Assert
        assert sm.recovery_attempts == 2
    
    def _create_mock_state_machine(self):
        """Создание машины состояний с mock подсистемами"""
        navigation = Mock()
        audio = Mock()
        order_verifier = Mock()
        serial_comm = Mock()
        lidar = Mock()
        box_controller = Mock()
        
        return StateMachine(navigation, audio, order_verifier, serial_comm, lidar, box_controller)


class TestStateUpdate:
    """Тесты обновления состояний"""
    
    def test_update_calls_correct_state_handler(self):
        """Тест: update вызывает правильный обработчик состояния"""
        # Arrange
        sm = self._create_mock_state_machine()
        sm.navigation.get_current_position.return_value = (0.0, 0.0, 0.0)
        sm.lidar.detect_person.return_value = None
        
        # Act
        sm.update()
        
        # Assert
        sm.navigation.update_localization.assert_called_once()
        sm.lidar.detect_person.assert_called_once()
    
    def test_update_handles_exceptions(self):
        """Тест: update обрабатывает исключения"""
        # Arrange
        sm = self._create_mock_state_machine()
        sm.navigation.update_localization.side_effect = RuntimeError("Localization error")
        
        # Act
        sm.update()
        
        # Assert
        assert sm.current_state == State.ERROR_RECOVERY
    
    def _create_mock_state_machine(self):
        """Создание машины состояний с mock подсистемами"""
        navigation = Mock()
        audio = Mock()
        order_verifier = Mock()
        serial_comm = Mock()
        lidar = Mock()
        box_controller = Mock()
        
        return StateMachine(navigation, audio, order_verifier, serial_comm, lidar, box_controller)


class TestStartStop:
    """Тесты запуска и остановки машины состояний"""
    
    def test_start_sets_running_flag(self):
        """Тест: start устанавливает флаг is_running"""
        # Arrange
        sm = self._create_mock_state_machine()
        
        # Act
        sm.start()
        
        # Assert
        assert sm.is_running == True
        assert sm.current_state == State.WAITING
    
    def test_stop_clears_running_flag(self):
        """Тест: stop сбрасывает флаг is_running"""
        # Arrange
        sm = self._create_mock_state_machine()
        sm.start()
        
        # Act
        sm.stop()
        
        # Assert
        assert sm.is_running == False
        sm.navigation.stop.assert_called_once()
        sm.box_controller.close.assert_called_once()
    
    def _create_mock_state_machine(self):
        """Создание машины состояний с mock подсистемами"""
        navigation = Mock()
        audio = Mock()
        order_verifier = Mock()
        serial_comm = Mock()
        lidar = Mock()
        box_controller = Mock()
        
        return StateMachine(navigation, audio, order_verifier, serial_comm, lidar, box_controller)
