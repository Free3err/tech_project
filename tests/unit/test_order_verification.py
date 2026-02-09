"""
Модульные тесты для системы проверки заказов

Тестирует OrderVerificationSystem класс из qrScanner.py
"""

import json
import pytest
import sys
from unittest.mock import Mock, MagicMock, patch

# Мокируем внешние зависимости перед импортом qrScanner
sys.modules['cv2'] = MagicMock()
sys.modules['playsound3'] = MagicMock()
sys.modules['serialConnection'] = MagicMock()

from qrScanner import OrderVerificationSystem


class TestOrderVerificationSystem:
    """Тесты для класса OrderVerificationSystem"""
    
    def test_init(self):
        """Тест инициализации системы проверки заказов"""
        ovs = OrderVerificationSystem()
        assert ovs.scanning is False
        assert ovs.callback is None
        assert ovs.last_data is None
        assert ovs.detector is not None
        
    def test_verify_order_valid_json(self):
        """Тест проверки заказа с валидным JSON"""
        ovs = OrderVerificationSystem()
        
        # Создаем валидный QR код
        order_data = json.dumps({
            "order_id": 123,
            "secret_key": "test_secret_key"
        })
        
        # Мокируем check_order для возврата True
        with patch('qrScanner.check_order', return_value=True):
            is_valid, order_id = ovs.verify_order(order_data)
            
        assert is_valid is True
        assert order_id == 123
        
    def test_verify_order_invalid_credentials(self):
        """Тест проверки заказа с неверными учетными данными"""
        ovs = OrderVerificationSystem()
        
        # Создаем QR код с неверными данными
        order_data = json.dumps({
            "order_id": 999,
            "secret_key": "wrong_key"
        })
        
        # Мокируем check_order для возврата False
        with patch('qrScanner.check_order', return_value=False):
            is_valid, order_id = ovs.verify_order(order_data)
            
        assert is_valid is False
        assert order_id == 999
        
    def test_verify_order_malformed_json(self):
        """Тест проверки заказа с некорректным JSON"""
        ovs = OrderVerificationSystem()
        
        # Некорректный JSON
        order_data = "not a json string"
        
        is_valid, order_id = ovs.verify_order(order_data)
        
        assert is_valid is False
        assert order_id is None
        
    def test_verify_order_missing_fields(self):
        """Тест проверки заказа с отсутствующими полями"""
        ovs = OrderVerificationSystem()
        
        # JSON без обязательных полей
        order_data = json.dumps({"order_id": 123})  # Нет secret_key
        
        is_valid, order_id = ovs.verify_order(order_data)
        
        assert is_valid is False
        assert order_id is None
        
    def test_verify_order_empty_json(self):
        """Тест проверки заказа с пустым JSON"""
        ovs = OrderVerificationSystem()
        
        order_data = json.dumps({})
        
        is_valid, order_id = ovs.verify_order(order_data)
        
        assert is_valid is False
        assert order_id is None
        
    def test_stop_scanning_when_not_scanning(self):
        """Тест остановки сканирования когда оно не запущено"""
        ovs = OrderVerificationSystem()
        
        # Не должно вызывать ошибок
        ovs.stop_scanning()
        
        assert ovs.scanning is False
        assert ovs.cap is None
        
    def test_start_scanning_sets_callback(self):
        """Тест что start_scanning устанавливает callback"""
        ovs = OrderVerificationSystem()
        
        callback = Mock()
        
        # Мокируем Thread чтобы не запускать реальное сканирование
        with patch('qrScanner.threading.Thread') as mock_thread:
            ovs.start_scanning(callback)
            
        assert ovs.callback == callback
        assert ovs.scanning is True
        assert mock_thread.called
        
    def test_start_scanning_ignores_if_already_scanning(self):
        """Тест что start_scanning игнорируется если уже идет сканирование"""
        ovs = OrderVerificationSystem()
        ovs.scanning = True
        
        callback = Mock()
        
        with patch('qrScanner.threading.Thread') as mock_thread:
            ovs.start_scanning(callback)
            
        # Thread не должен быть создан
        assert not mock_thread.called
        
    def test_verify_order_with_special_characters(self):
        """Тест проверки заказа с специальными символами в secret_key"""
        ovs = OrderVerificationSystem()
        
        order_data = json.dumps({
            "order_id": 456,
            "secret_key": "key_with_!@#$%_special"
        })
        
        with patch('qrScanner.check_order', return_value=True):
            is_valid, order_id = ovs.verify_order(order_data)
            
        assert is_valid is True
        assert order_id == 456
        
    def test_verify_order_with_large_order_id(self):
        """Тест проверки заказа с большим order_id"""
        ovs = OrderVerificationSystem()
        
        order_data = json.dumps({
            "order_id": 999999999,
            "secret_key": "test_key"
        })
        
        with patch('qrScanner.check_order', return_value=True):
            is_valid, order_id = ovs.verify_order(order_data)
            
        assert is_valid is True
        assert order_id == 999999999
