#!/usr/bin/env python3
"""
Audio File Generator for RelayBot
Генератор аудио файлов для RelayBot

This script generates all required audio files using gTTS and converts them to WAV format.
Этот скрипт генерирует все необходимые аудио файлы используя gTTS и конвертирует их в формат WAV.

Requirements:
    pip install gtts pydub

System requirements:
    ffmpeg must be installed for pydub to work
    
Usage:
    python generate_audio_files.py
"""

from gtts import gTTS
from pydub import AudioSegment
import os
from pathlib import Path
import sys

# Output directory
OUTPUT_DIR = Path('assets/audio')

# Russian number dictionary
RUSSIAN_NUMBERS = {
    1: 'один', 2: 'два', 3: 'три', 4: 'четыре', 5: 'пять',
    6: 'шесть', 7: 'семь', 8: 'восемь', 9: 'девять', 10: 'десять',
    11: 'одиннадцать', 12: 'двенадцать', 13: 'тринадцать',
    14: 'четырнадцать', 15: 'пятнадцать', 16: 'шестнадцать',
    17: 'семнадцать', 18: 'восемнадцать', 19: 'девятнадцать',
    20: 'двадцать', 30: 'тридцать', 40: 'сорок', 50: 'пятьдесят',
    60: 'шестьдесят', 70: 'семьдесят', 80: 'восемьдесят', 90: 'девяносто',
    100: 'сто'
}


def number_to_russian(n):
    """
    Convert number to Russian text
    Конвертировать число в русский текст
    
    Args:
        n: Number to convert (1-100)
        
    Returns:
        Russian text representation of the number
    """
    if n in RUSSIAN_NUMBERS:
        return RUSSIAN_NUMBERS[n]
    elif n < 100:
        tens = (n // 10) * 10
        ones = n % 10
        return f"{RUSSIAN_NUMBERS[tens]} {RUSSIAN_NUMBERS[ones]}"
    return str(n)


def check_dependencies():
    """
    Check if required dependencies are installed
    Проверить установлены ли необходимые зависимости
    
    Returns:
        True if all dependencies are available, False otherwise
    """
    try:
        import gtts
        import pydub
        print("✓ Python dependencies (gtts, pydub) are installed")
    except ImportError as e:
        print(f"✗ Missing Python dependency: {e}")
        print("  Install with: pip install gtts pydub")
        return False
    
    # Check ffmpeg
    try:
        from pydub.utils import which
        if which("ffmpeg") is None:
            print("✗ ffmpeg is not installed or not in PATH")
            print("  Install ffmpeg:")
            print("    Ubuntu/Debian: sudo apt-get install ffmpeg")
            print("    macOS: brew install ffmpeg")
            print("    Windows: Download from https://ffmpeg.org/")
            return False
        print("✓ ffmpeg is installed")
    except Exception as e:
        print(f"⚠ Could not verify ffmpeg installation: {e}")
    
    return True


def generate_audio_file(text, filename, lang='ru'):
    """
    Generate audio file from text using gTTS and convert to WAV
    Генерировать аудио файл из текста используя gTTS и конвертировать в WAV
    
    Args:
        text: Text to convert to speech
        filename: Output filename (without extension)
        lang: Language code (default: 'ru' for Russian)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate MP3 using gTTS
        mp3_path = OUTPUT_DIR / f"{filename}.mp3"
        wav_path = OUTPUT_DIR / f"{filename}.wav"
        
        # Skip if WAV already exists
        if wav_path.exists():
            print(f"⊙ Skipping {filename}.wav (already exists)")
            return True
        
        print(f"Generating {filename}...", end=' ')
        
        # Generate speech
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(str(mp3_path))
        
        # Convert MP3 to WAV
        audio = AudioSegment.from_mp3(str(mp3_path))
        audio = audio.set_channels(1)  # Mono
        audio = audio.set_frame_rate(44100)  # 44.1kHz
        audio = audio.set_sample_width(2)  # 16-bit
        
        # Normalize volume to -3dB
        audio = audio.normalize(headroom=3.0)
        
        # Export as WAV
        audio.export(str(wav_path), format='wav')
        
        # Remove temporary MP3
        mp3_path.unlink()
        
        print(f"✓")
        return True
        
    except Exception as e:
        print(f"✗")
        print(f"  Error: {e}")
        return False


def main():
    """
    Main function to generate all audio files
    Главная функция для генерации всех аудио файлов
    """
    print("=" * 70)
    print("RelayBot Audio File Generator")
    print("Генератор аудио файлов RelayBot")
    print("=" * 70)
    print()
    
    # Check dependencies
    print("Checking dependencies...")
    print("Проверка зависимостей...")
    print()
    if not check_dependencies():
        print()
        print("✗ Please install missing dependencies and try again.")
        print("✗ Пожалуйста, установите недостающие зависимости и попробуйте снова.")
        sys.exit(1)
    
    print()
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR.absolute()}")
    print()
    
    # Core system prompts
    print("-" * 70)
    print("Generating core system prompts...")
    print("Генерация основных системных подсказок...")
    print("-" * 70)
    
    core_prompts = {
        'request_qr': 'Пожалуйста, покажите QR код вашего заказа',
        'order_accepted': 'Заказ принят. Еду на склад.',
        'order_rejected': 'Заказ не найден. Пожалуйста, проверьте QR код.',
        'delivery_greeting': 'Ваш заказ доставлен. Приятного дня!'
    }
    
    success_count = 0
    for filename, text in core_prompts.items():
        if generate_audio_file(text, filename):
            success_count += 1
    
    print()
    print(f"Core prompts: {success_count}/{len(core_prompts)} generated")
    print()
    
    # Order number announcements
    print("-" * 70)
    print("Generating order number announcements (1-100)...")
    print("Генерация объявлений номеров заказов (1-100)...")
    print("-" * 70)
    
    order_success = 0
    for i in range(1, 101):
        text = f"Заказ номер {number_to_russian(i)}"
        filename = f"order_{i}"
        if generate_audio_file(text, filename):
            order_success += 1
        
        # Progress indicator every 10 files
        if i % 10 == 0:
            print(f"  Progress: {i}/100 files")
    
    print()
    print(f"Order numbers: {order_success}/100 generated")
    print()
    
    # Summary
    total_files = len(core_prompts) + 100
    total_success = success_count + order_success
    
    print("=" * 70)
    print("SUMMARY / ИТОГИ")
    print("=" * 70)
    print(f"Total files generated: {total_success}/{total_files}")
    print(f"Success rate: {(total_success/total_files)*100:.1f}%")
    print()
    print(f"Audio files location: {OUTPUT_DIR.absolute()}")
    print()
    
    if total_success == total_files:
        print("✓ All audio files generated successfully!")
        print("✓ Все аудио файлы успешно сгенерированы!")
        print()
        print("Next steps:")
        print("1. Test audio playback: python -c \"from playsound3 import playsound; playsound('assets/audio/request_qr.wav')\"")
        print("2. Verify audio quality by listening to sample files")
        print("3. Move existing successScan.wav and failureScan.wav to assets/audio/")
    else:
        print("⚠ Some files failed to generate. Check errors above.")
        print("⚠ Некоторые файлы не удалось сгенерировать. Проверьте ошибки выше.")
        print()
        print("Common issues:")
        print("- No internet connection (gTTS requires internet)")
        print("- ffmpeg not installed or not in PATH")
        print("- Insufficient disk space")
    
    print("=" * 70)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        print()
        print("⚠ Generation interrupted by user")
        print("⚠ Генерация прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print()
        print()
        print(f"✗ Unexpected error: {e}")
        print(f"✗ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
