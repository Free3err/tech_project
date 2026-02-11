#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для диагностики микрофона
Проверяет доступные аудио устройства и тестирует запись
"""

import sys

print("=" * 80)
print("ДИАГНОСТИКА МИКРОФОНА")
print("=" * 80)

# 1. Проверка PyAudio
print("\n1. Проверка PyAudio...")
try:
    import pyaudio
    print("✓ PyAudio установлен")
    
    # Получение списка устройств
    p = pyaudio.PyAudio()
    print(f"\nВсего аудио устройств: {p.get_device_count()}")
    print("\nСписок устройств:")
    print("-" * 80)
    
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        print(f"\nУстройство {i}:")
        print(f"  Название: {info['name']}")
        print(f"  Входных каналов: {info['maxInputChannels']}")
        print(f"  Выходных каналов: {info['maxOutputChannels']}")
        print(f"  Частота дискретизации: {info['defaultSampleRate']} Hz")
        
        # Отмечаем устройства с микрофоном
        if info['maxInputChannels'] > 0:
            print(f"  >>> МИКРОФОН ДОСТУПЕН <<<")
    
    # Получение устройства по умолчанию
    try:
        default_input = p.get_default_input_device_info()
        print("\n" + "=" * 80)
        print("УСТРОЙСТВО ВВОДА ПО УМОЛЧАНИЮ:")
        print(f"  Индекс: {default_input['index']}")
        print(f"  Название: {default_input['name']}")
        print(f"  Входных каналов: {default_input['maxInputChannels']}")
        print("=" * 80)
    except Exception as e:
        print(f"\n⚠ Не удалось получить устройство ввода по умолчанию: {e}")
    
    p.terminate()
    
except ImportError:
    print("✗ PyAudio не установлен")
    print("Установите: pip install PyAudio")
    sys.exit(1)
except Exception as e:
    print(f"✗ Ошибка при работе с PyAudio: {e}")
    sys.exit(1)

# 2. Проверка SpeechRecognition
print("\n\n2. Проверка SpeechRecognition...")
try:
    import speech_recognition as sr
    print("✓ SpeechRecognition установлен")
    print(f"  Версия: {sr.__version__}")
except ImportError:
    print("✗ SpeechRecognition не установлен")
    print("Установите: pip install SpeechRecognition")
    sys.exit(1)

# 3. Тест записи с микрофона
print("\n\n3. Тест записи с микрофона...")
print("Выберите устройство для теста (введите номер) или Enter для устройства по умолчанию:")

device_index = input("Номер устройства: ").strip()
if device_index:
    device_index = int(device_index)
else:
    device_index = None

print(f"\nИспользуется устройство: {device_index if device_index is not None else 'по умолчанию'}")

try:
    recognizer = sr.Recognizer()
    
    # Создание микрофона с указанным устройством
    if device_index is not None:
        mic = sr.Microphone(device_index=device_index)
    else:
        mic = sr.Microphone()
    
    print("\nНастройка микрофона (калибровка шума)...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
        print(f"✓ Калибровка завершена. Уровень шума: {recognizer.energy_threshold}")
        
        print("\nГоворите что-нибудь (5 секунд)...")
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            print("✓ Аудио записано")
            
            # Попытка распознавания
            print("\nРаспознавание речи (Google Speech Recognition)...")
            try:
                text = recognizer.recognize_google(audio, language='ru-RU')
                print(f"✓ Распознано: '{text}'")
            except sr.UnknownValueError:
                print("⚠ Не удалось распознать речь (возможно, ничего не было сказано)")
            except sr.RequestError as e:
                print(f"✗ Ошибка сервиса распознавания: {e}")
                
        except sr.WaitTimeoutError:
            print("⚠ Таймаут ожидания речи (ничего не было сказано)")
            
except Exception as e:
    print(f"✗ Ошибка при тестировании микрофона: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("ДИАГНОСТИКА ЗАВЕРШЕНА")
print("=" * 80)
