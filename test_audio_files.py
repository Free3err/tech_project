#!/usr/bin/env python3
"""
Audio Files Test Script for RelayBot
Скрипт тестирования аудио файлов для RelayBot

This script verifies that all required audio files exist and can be played.
Этот скрипт проверяет, что все необходимые аудио файлы существуют и могут быть воспроизведены.

Usage:
    python test_audio_files.py [--play-samples]
"""

import os
import sys
from pathlib import Path
import argparse

# Audio directory
AUDIO_DIR = Path('assets/audio')

# Required core files
CORE_FILES = [
    'request_qr.wav',
    'order_accepted.wav',
    'order_rejected.wav',
    'delivery_greeting.wav'
]

# Required order number files (1-100)
ORDER_FILES = [f'order_{i}.wav' for i in range(1, 101)]

# Optional existing files
OPTIONAL_FILES = [
    'successScan.wav',
    'failureScan.wav'
]


def check_file_exists(filename):
    """
    Check if a file exists in the audio directory
    Проверить существует ли файл в директории аудио
    
    Args:
        filename: Name of the file to check
        
    Returns:
        True if file exists, False otherwise
    """
    filepath = AUDIO_DIR / filename
    return filepath.exists() and filepath.is_file()


def check_file_properties(filename):
    """
    Check basic properties of an audio file
    Проверить базовые свойства аудио файла
    
    Args:
        filename: Name of the file to check
        
    Returns:
        Dictionary with file properties or None if file doesn't exist
    """
    filepath = AUDIO_DIR / filename
    if not filepath.exists():
        return None
    
    try:
        import wave
        with wave.open(str(filepath), 'rb') as wav_file:
            return {
                'channels': wav_file.getnchannels(),
                'sample_rate': wav_file.getframerate(),
                'sample_width': wav_file.getsampwidth(),
                'duration': wav_file.getnframes() / wav_file.getframerate(),
                'size_kb': filepath.stat().st_size / 1024
            }
    except Exception as e:
        return {'error': str(e)}


def play_audio_file(filename):
    """
    Play an audio file
    Воспроизвести аудио файл
    
    Args:
        filename: Name of the file to play
        
    Returns:
        True if successful, False otherwise
    """
    filepath = AUDIO_DIR / filename
    if not filepath.exists():
        print(f"  ✗ File not found: {filename}")
        return False
    
    try:
        from playsound3 import playsound
        print(f"  ▶ Playing {filename}...")
        playsound(str(filepath))
        print(f"  ✓ Playback complete")
        return True
    except ImportError:
        print(f"  ⚠ playsound3 not installed. Install with: pip install playsound3")
        return False
    except Exception as e:
        print(f"  ✗ Error playing {filename}: {e}")
        return False


def main():
    """
    Main function to test audio files
    Главная функция для тестирования аудио файлов
    """
    parser = argparse.ArgumentParser(
        description='Test RelayBot audio files / Тестировать аудио файлы RelayBot'
    )
    parser.add_argument(
        '--play-samples',
        action='store_true',
        help='Play sample audio files / Воспроизвести образцы аудио файлов'
    )
    parser.add_argument(
        '--check-properties',
        action='store_true',
        help='Check audio file properties / Проверить свойства аудио файлов'
    )
    args = parser.parse_args()
    
    print("=" * 70)
    print("RelayBot Audio Files Test")
    print("Тест аудио файлов RelayBot")
    print("=" * 70)
    print()
    
    # Check if audio directory exists
    if not AUDIO_DIR.exists():
        print(f"✗ Audio directory not found: {AUDIO_DIR}")
        print(f"✗ Директория аудио не найдена: {AUDIO_DIR}")
        print()
        print("Please create the directory and generate audio files first.")
        print("Пожалуйста, создайте директорию и сгенерируйте аудио файлы сначала.")
        sys.exit(1)
    
    print(f"Audio directory: {AUDIO_DIR.absolute()}")
    print()
    
    # Test core files
    print("-" * 70)
    print("Testing core system prompts...")
    print("Тестирование основных системных подсказок...")
    print("-" * 70)
    
    core_missing = []
    core_present = []
    
    for filename in CORE_FILES:
        if check_file_exists(filename):
            print(f"✓ {filename}")
            core_present.append(filename)
            
            if args.check_properties:
                props = check_file_properties(filename)
                if props and 'error' not in props:
                    print(f"  Channels: {props['channels']}, "
                          f"Sample Rate: {props['sample_rate']} Hz, "
                          f"Duration: {props['duration']:.2f}s, "
                          f"Size: {props['size_kb']:.1f} KB")
        else:
            print(f"✗ {filename} - MISSING")
            core_missing.append(filename)
    
    print()
    print(f"Core files: {len(core_present)}/{len(CORE_FILES)} present")
    print()
    
    # Test order number files
    print("-" * 70)
    print("Testing order number announcements (1-100)...")
    print("Тестирование объявлений номеров заказов (1-100)...")
    print("-" * 70)
    
    order_missing = []
    order_present = []
    
    for filename in ORDER_FILES:
        if check_file_exists(filename):
            order_present.append(filename)
        else:
            order_missing.append(filename)
    
    # Show progress in groups of 10
    for i in range(0, 100, 10):
        start = i + 1
        end = min(i + 10, 100)
        group_files = ORDER_FILES[i:end]
        group_present = sum(1 for f in group_files if f in order_present)
        status = "✓" if group_present == len(group_files) else "✗"
        print(f"{status} order_{start}.wav - order_{end}.wav: {group_present}/{len(group_files)}")
    
    print()
    print(f"Order files: {len(order_present)}/{len(ORDER_FILES)} present")
    print()
    
    # Test optional files
    print("-" * 70)
    print("Testing optional sound effects...")
    print("Тестирование опциональных звуковых эффектов...")
    print("-" * 70)
    
    optional_present = []
    for filename in OPTIONAL_FILES:
        if check_file_exists(filename):
            print(f"✓ {filename}")
            optional_present.append(filename)
        else:
            print(f"⊙ {filename} - not present (optional)")
    
    print()
    print(f"Optional files: {len(optional_present)}/{len(OPTIONAL_FILES)} present")
    print()
    
    # Summary
    total_required = len(CORE_FILES) + len(ORDER_FILES)
    total_present = len(core_present) + len(order_present)
    total_missing = len(core_missing) + len(order_missing)
    
    print("=" * 70)
    print("SUMMARY / ИТОГИ")
    print("=" * 70)
    print(f"Required files: {total_present}/{total_required} present")
    print(f"Missing files: {total_missing}")
    print(f"Optional files: {len(optional_present)}/{len(OPTIONAL_FILES)} present")
    print()
    
    if total_missing == 0:
        print("✓ All required audio files are present!")
        print("✓ Все необходимые аудио файлы присутствуют!")
    else:
        print("✗ Some required files are missing.")
        print("✗ Некоторые необходимые файлы отсутствуют.")
        print()
        print("Missing files:")
        for filename in core_missing + order_missing:
            print(f"  - {filename}")
        print()
        print("Generate missing files with: python generate_audio_files.py")
        print("Сгенерируйте отсутствующие файлы: python generate_audio_files.py")
    
    print("=" * 70)
    
    # Play samples if requested
    if args.play_samples and total_present > 0:
        print()
        print("-" * 70)
        print("Playing sample audio files...")
        print("Воспроизведение образцов аудио файлов...")
        print("-" * 70)
        print()
        
        samples = []
        if 'request_qr.wav' in core_present:
            samples.append('request_qr.wav')
        if 'order_accepted.wav' in core_present:
            samples.append('order_accepted.wav')
        if 'order_1.wav' in order_present:
            samples.append('order_1.wav')
        if 'order_50.wav' in order_present:
            samples.append('order_50.wav')
        if 'delivery_greeting.wav' in core_present:
            samples.append('delivery_greeting.wav')
        
        for filename in samples:
            play_audio_file(filename)
            print()
        
        print("-" * 70)
    
    # Exit code
    sys.exit(0 if total_missing == 0 else 1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        print()
        print("⚠ Test interrupted by user")
        print("⚠ Тест прерван пользователем")
        sys.exit(1)
    except Exception as e:
        print()
        print()
        print(f"✗ Unexpected error: {e}")
        print(f"✗ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
