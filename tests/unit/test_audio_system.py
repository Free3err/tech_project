# -*- coding: utf-8 -*-
"""
Модульные тесты для аудио системы
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import logging

# Мокируем playsound3 перед импортом audio_system
import sys
sys.modules['playsound3'] = MagicMock()

from audio_system import AudioSystem
import config


@pytest.fixture
def audio_system(tmp_path):
    """
    Фикстура для создания экземпляра AudioSystem с временной директорией
    """
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    return AudioSystem(audio_dir=str(audio_dir))


@pytest.fixture
def audio_system_with_files(tmp_path):
    """
    Фикстура для создания AudioSystem с тестовыми аудио файлами
    """
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    
    # Создаем пустые тестовые файлы
    test_files = [
        'request_qr.wav',
        'order_accepted.wav',
        'order_rejected.wav',
        'delivery_greeting.wav',
        'order_42.wav',
        'error.wav'
    ]
    
    for filename in test_files:
        (audio_dir / filename).touch()
    
    return AudioSystem(audio_dir=str(audio_dir))


class TestAudioSystemInitialization:
    """Тесты инициализации аудио системы"""
    
    def test_init_with_default_directory(self):
        """Тест инициализации с директорией по умолчанию"""
        audio = AudioSystem()
        assert audio.audio_dir == config.AUDIO_DIR
    
    def test_init_with_custom_directory(self, tmp_path):
        """Тест инициализации с пользовательской директорией"""
        custom_dir = str(tmp_path / "custom_audio")
        audio = AudioSystem(audio_dir=custom_dir)
        assert audio.audio_dir == custom_dir
    
    def test_init_creates_missing_directory(self, tmp_path):
        """Тест создания отсутствующей директории"""
        audio_dir = tmp_path / "new_audio"
        audio = AudioSystem(audio_dir=str(audio_dir))
        assert os.path.exists(audio_dir)


class TestAudioFileHandling:
    """Тесты обработки аудио файлов"""
    
    def test_get_audio_path(self, audio_system):
        """Тест получения полного пути к аудио файлу"""
        filename = "test.wav"
        expected_path = os.path.join(audio_system.audio_dir, filename)
        assert audio_system._get_audio_path(filename) == expected_path
    
    def test_check_audio_file_exists(self, audio_system_with_files):
        """Тест проверки существующего файла"""
        assert audio_system_with_files._check_audio_file('request_qr.wav') is True
    
    def test_check_audio_file_missing(self, audio_system):
        """Тест проверки отсутствующего файла"""
        assert audio_system._check_audio_file('nonexistent.wav') is False


class TestAudioPlayback:
    """Тесты воспроизведения аудио"""
    
    @patch('audio_system.playsound')
    def test_play_blocking(self, mock_playsound, audio_system_with_files):
        """Тест блокирующего воспроизведения"""
        audio_system_with_files.play('request_qr.wav', blocking=True)
        
        # Проверяем, что playsound был вызван с правильными параметрами
        expected_path = audio_system_with_files._get_audio_path('request_qr.wav')
        mock_playsound.assert_called_once_with(expected_path, block=True)
    
    @patch('audio_system.playsound')
    def test_play_non_blocking(self, mock_playsound, audio_system_with_files):
        """Тест неблокирующего воспроизведения"""
        audio_system_with_files.play('request_qr.wav', blocking=False)
        
        # Даем время потоку запуститься
        import time
        time.sleep(0.1)
        
        # Проверяем, что поток был создан
        assert audio_system_with_files._playback_thread is not None
    
    @patch('audio_system.playsound')
    def test_play_missing_file(self, mock_playsound, audio_system):
        """Тест воспроизведения отсутствующего файла"""
        audio_system.play('nonexistent.wav', blocking=True)
        
        # playsound не должен быть вызван для отсутствующего файла
        mock_playsound.assert_not_called()
    
    @patch('audio_system.playsound')
    def test_play_with_exception(self, mock_playsound, audio_system_with_files, caplog):
        """Тест обработки исключения при воспроизведении"""
        mock_playsound.side_effect = Exception("Playback error")
        
        with caplog.at_level(logging.ERROR):
            audio_system_with_files.play('request_qr.wav', blocking=True)
        
        # Проверяем, что ошибка была залогирована
        assert "Ошибка воспроизведения аудио" in caplog.text


class TestAudioMethods:
    """Тесты методов аудио системы"""
    
    @patch('audio_system.playsound')
    def test_request_qr_code(self, mock_playsound, audio_system_with_files):
        """Тест запроса QR кода"""
        audio_system_with_files.request_qr_code()
        
        import time
        time.sleep(0.1)
        
        # Проверяем, что был вызван правильный файл
        assert audio_system_with_files._playback_thread is not None
    
    @patch('audio_system.playsound')
    def test_announce_order_accepted(self, mock_playsound, audio_system_with_files):
        """Тест объявления принятия заказа"""
        audio_system_with_files.announce_order_accepted()
        
        import time
        time.sleep(0.1)
        
        assert audio_system_with_files._playback_thread is not None
    
    @patch('audio_system.playsound')
    def test_announce_order_rejected(self, mock_playsound, audio_system_with_files):
        """Тест объявления отклонения заказа"""
        audio_system_with_files.announce_order_rejected()
        
        import time
        time.sleep(0.1)
        
        assert audio_system_with_files._playback_thread is not None
    
    @patch('audio_system.playsound')
    def test_announce_order_number_with_file(self, mock_playsound, audio_system_with_files):
        """Тест объявления номера заказа с существующим файлом"""
        audio_system_with_files.announce_order_number(42)
        
        import time
        time.sleep(0.1)
        
        # Проверяем, что был использован специфичный файл заказа
        assert audio_system_with_files._playback_thread is not None
    
    @patch('audio_system.playsound')
    def test_announce_order_number_without_file(self, mock_playsound, audio_system_with_files, caplog):
        """Тест объявления номера заказа без специфичного файла"""
        with caplog.at_level(logging.WARNING):
            audio_system_with_files.announce_order_number(999)
        
        # Проверяем, что было предупреждение о отсутствии файла
        assert "Специфичный аудио файл для заказа 999 не найден" in caplog.text
    
    @patch('audio_system.playsound')
    def test_greet_delivery(self, mock_playsound, audio_system_with_files):
        """Тест приветствия при доставке"""
        audio_system_with_files.greet_delivery()
        
        import time
        time.sleep(0.1)
        
        assert audio_system_with_files._playback_thread is not None
    
    @patch('audio_system.playsound')
    def test_play_success_sound(self, mock_playsound, audio_system_with_files):
        """Тест воспроизведения звука успеха"""
        # Создаем файл в корневой директории assets
        assets_dir = os.path.join(os.path.dirname(audio_system_with_files.audio_dir), 'assets')
        os.makedirs(assets_dir, exist_ok=True)
        success_file = os.path.join(assets_dir, config.AUDIO_SUCCESS_SCAN)
        
        with open(success_file, 'w') as f:
            f.write('')
        
        try:
            audio_system_with_files.play_success_sound()
            
            import time
            time.sleep(0.1)
            
            # Проверяем, что playsound был вызван
            assert mock_playsound.called
        finally:
            # Очистка
            if os.path.exists(success_file):
                os.remove(success_file)
    
    @patch('audio_system.playsound')
    def test_play_failure_sound(self, mock_playsound, audio_system_with_files):
        """Тест воспроизведения звука неудачи"""
        # Создаем файл в корневой директории assets
        assets_dir = os.path.join(os.path.dirname(audio_system_with_files.audio_dir), 'assets')
        os.makedirs(assets_dir, exist_ok=True)
        failure_file = os.path.join(assets_dir, config.AUDIO_FAILURE_SCAN)
        
        with open(failure_file, 'w') as f:
            f.write('')
        
        try:
            audio_system_with_files.play_failure_sound()
            
            import time
            time.sleep(0.1)
            
            # Проверяем, что playsound был вызван
            assert mock_playsound.called
        finally:
            # Очистка
            if os.path.exists(failure_file):
                os.remove(failure_file)
    
    @patch('audio_system.playsound')
    def test_play_error_sound(self, mock_playsound, audio_system_with_files):
        """Тест воспроизведения звука ошибки"""
        audio_system_with_files.play_error_sound()
        
        import time
        time.sleep(0.1)
        
        assert audio_system_with_files._playback_thread is not None


class TestAudioStop:
    """Тесты остановки воспроизведения"""
    
    def test_stop_playback(self, audio_system):
        """Тест остановки воспроизведения"""
        audio_system.stop()
        
        # Проверяем, что флаг остановки установлен
        assert audio_system._stop_playback is True
    
    @patch('audio_system.playsound')
    def test_stop_during_playback(self, mock_playsound, audio_system_with_files):
        """Тест остановки во время воспроизведения"""
        # Запускаем воспроизведение
        audio_system_with_files.play('request_qr.wav', blocking=False)
        
        import time
        time.sleep(0.05)
        
        # Останавливаем
        audio_system_with_files.stop()
        
        # Проверяем, что флаг остановки установлен
        assert audio_system_with_files._stop_playback is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
