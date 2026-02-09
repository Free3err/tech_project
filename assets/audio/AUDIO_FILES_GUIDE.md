# RelayBot Audio Files Guide / Руководство по аудио файлам RelayBot

## Overview / Обзор

This document provides comprehensive instructions for generating all required audio files for the RelayBot autonomous delivery system. Since audio files cannot be generated programmatically within the codebase, this guide lists all required files, their Russian text content, and instructions for generating them using text-to-speech (TTS) tools.

Этот документ содержит подробные инструкции по созданию всех необходимых аудио файлов для автономной системы доставки RelayBot. Поскольку аудио файлы не могут быть созданы программно в коде, это руководство перечисляет все необходимые файлы, их русский текстовый контент и инструкции по их созданию с использованием инструментов преобразования текста в речь (TTS).

## Audio Format Requirements / Требования к формату аудио

All audio files must meet the following specifications:

- **Format**: WAV (Waveform Audio File Format)
- **Sample Rate**: 44100 Hz (CD quality) or 22050 Hz (acceptable)
- **Bit Depth**: 16-bit
- **Channels**: Mono (1 channel) - preferred for smaller file size
- **Encoding**: PCM (Pulse Code Modulation)
- **Language**: Russian (Русский)
- **Voice**: Female or male, clear and friendly tone
- **Volume**: Normalized to -3dB to prevent clipping

Все аудио файлы должны соответствовать следующим спецификациям:

- **Формат**: WAV (Waveform Audio File Format)
- **Частота дискретизации**: 44100 Гц (качество CD) или 22050 Гц (приемлемо)
- **Разрядность**: 16 бит
- **Каналы**: Моно (1 канал) - предпочтительно для меньшего размера файла
- **Кодирование**: PCM (импульсно-кодовая модуляция)
- **Язык**: Русский
- **Голос**: Женский или мужской, четкий и дружелюбный тон
- **Громкость**: Нормализована до -3дБ для предотвращения искажений

## Required Audio Files / Необходимые аудио файлы

### 1. Core System Prompts / Основные системные подсказки

#### request_qr.wav
- **Russian Text**: "Пожалуйста, покажите QR код вашего заказа"
- **English Translation**: "Please show the QR code of your order"
- **Usage**: Played when robot reaches customer and requests order verification
- **Duration**: ~3-4 seconds
- **Requirement**: 13.1

#### order_accepted.wav
- **Russian Text**: "Заказ принят. Еду на склад."
- **English Translation**: "Order accepted. Going to the warehouse."
- **Usage**: Played when order is successfully verified
- **Duration**: ~2-3 seconds
- **Requirement**: 13.2

#### order_rejected.wav
- **Russian Text**: "Заказ не найден. Пожалуйста, проверьте QR код."
- **English Translation**: "Order not found. Please check the QR code."
- **Usage**: Played when order verification fails
- **Duration**: ~3-4 seconds
- **Requirement**: 13.3

#### delivery_greeting.wav
- **Russian Text**: "Ваш заказ доставлен. Приятного дня!"
- **English Translation**: "Your order has been delivered. Have a nice day!"
- **Usage**: Played when robot returns to customer with package
- **Duration**: ~3-4 seconds
- **Requirement**: 13.5

### 2. Order Number Announcements / Объявления номеров заказов

The system requires audio files for announcing order numbers at the warehouse loading zone. You need to create 100 files for order numbers 1 through 100.

Системе требуются аудио файлы для объявления номеров заказов в зоне загрузки склада. Необходимо создать 100 файлов для номеров заказов от 1 до 100.

#### order_1.wav through order_100.wav
- **Russian Text Pattern**: "Заказ номер [NUMBER]"
- **English Translation**: "Order number [NUMBER]"
- **Usage**: Played at warehouse to announce which order to load
- **Duration**: ~2 seconds each
- **Requirement**: 13.4

**Examples**:
- `order_1.wav`: "Заказ номер один"
- `order_2.wav`: "Заказ номер два"
- `order_10.wav`: "Заказ номер десять"
- `order_25.wav`: "Заказ номер двадцать пять"
- `order_100.wav`: "Заказ номер сто"

**Complete list of Russian number pronunciations**:
- 1-10: один, два, три, четыре, пять, шесть, семь, восемь, девять, десять
- 11-19: одиннадцать, двенадцать, тринадцать, четырнадцать, пятнадцать, шестнадцать, семнадцать, восемнадцать, девятнадцать
- 20-90 (tens): двадцать, тридцать, сорок, пятьдесят, шестьдесят, семьдесят, восемьдесят, девяносто
- 100: сто

**Compound numbers** (21-99): Combine tens + ones
- 21: двадцать один
- 35: тридцать пять
- 47: сорок семь
- 99: девяносто девять

### 3. Existing Audio Files / Существующие аудио файлы

These files already exist in the assets directory and should be moved to assets/audio/:

Эти файлы уже существуют в директории assets и должны быть перемещены в assets/audio/:

#### successScan.wav
- **Usage**: Success sound effect for QR code scanning
- **Location**: Currently in assets/, should be in assets/audio/
- **Note**: This is a sound effect, not voice

#### failureScan.wav
- **Usage**: Failure sound effect for QR code scanning
- **Location**: Currently in assets/, should be in assets/audio/
- **Note**: This is a sound effect, not voice

## Text-to-Speech (TTS) Generation Methods / Методы генерации TTS

### Method 1: Online TTS Services / Онлайн сервисы TTS

#### Google Cloud Text-to-Speech
1. Visit: https://cloud.google.com/text-to-speech
2. Select language: Russian (ru-RU)
3. Select voice: ru-RU-Wavenet-A (female) or ru-RU-Wavenet-B (male)
4. Enter text and download WAV file
5. Repeat for all required phrases

#### Microsoft Azure Speech Service
1. Visit: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech/
2. Select language: Russian (Russia)
3. Select voice: ru-RU-SvetlanaNeural or ru-RU-DmitryNeural
4. Generate and download audio files

#### Yandex SpeechKit (Recommended for Russian)
1. Visit: https://cloud.yandex.com/en/services/speechkit
2. Best quality for Russian language
3. Multiple voice options available
4. API available for batch generation

### Method 2: Python TTS Libraries / Python библиотеки TTS

#### Using gTTS (Google Text-to-Speech)

```python
from gtts import gTTS
import os

# Create output directory
os.makedirs('assets/audio', exist_ok=True)

# Core prompts
prompts = {
    'request_qr.wav': 'Пожалуйста, покажите QR код вашего заказа',
    'order_accepted.wav': 'Заказ принят. Еду на склад.',
    'order_rejected.wav': 'Заказ не найден. Пожалуйста, проверьте QR код.',
    'delivery_greeting.wav': 'Ваш заказ доставлен. Приятного дня!'
}

# Generate core prompts
for filename, text in prompts.items():
    tts = gTTS(text=text, lang='ru', slow=False)
    mp3_file = filename.replace('.wav', '.mp3')
    tts.save(f'assets/audio/{mp3_file}')
    # Convert MP3 to WAV using pydub or ffmpeg
    print(f"Generated {filename}")

# Generate order numbers
russian_numbers = {
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
    """Convert number to Russian text"""
    if n in russian_numbers:
        return russian_numbers[n]
    elif n < 100:
        tens = (n // 10) * 10
        ones = n % 10
        return f"{russian_numbers[tens]} {russian_numbers[ones]}"
    return str(n)

# Generate order number files
for i in range(1, 101):
    text = f"Заказ номер {number_to_russian(i)}"
    tts = gTTS(text=text, lang='ru', slow=False)
    mp3_file = f'order_{i}.mp3'
    tts.save(f'assets/audio/{mp3_file}')
    # Convert MP3 to WAV using pydub or ffmpeg
    print(f"Generated order_{i}.wav")
```

**Note**: gTTS generates MP3 files. You need to convert them to WAV format using ffmpeg or pydub.

#### Converting MP3 to WAV using ffmpeg

```bash
# Install ffmpeg first
# Ubuntu/Debian: sudo apt-get install ffmpeg
# macOS: brew install ffmpeg
# Windows: Download from https://ffmpeg.org/

# Convert single file
ffmpeg -i input.mp3 -acodec pcm_s16le -ar 44100 -ac 1 output.wav

# Batch convert all MP3 files in directory
for file in assets/audio/*.mp3; do
    ffmpeg -i "$file" -acodec pcm_s16le -ar 44100 -ac 1 "${file%.mp3}.wav"
    rm "$file"  # Remove MP3 after conversion
done
```

#### Using pydub for conversion

```python
from pydub import AudioSegment
import os

# Convert MP3 to WAV
def convert_mp3_to_wav(mp3_path, wav_path):
    audio = AudioSegment.from_mp3(mp3_path)
    audio = audio.set_channels(1)  # Mono
    audio = audio.set_frame_rate(44100)  # 44.1kHz
    audio = audio.set_sample_width(2)  # 16-bit
    audio.export(wav_path, format='wav')
    os.remove(mp3_path)  # Remove MP3

# Batch convert
for filename in os.listdir('assets/audio'):
    if filename.endswith('.mp3'):
        mp3_path = os.path.join('assets/audio', filename)
        wav_path = mp3_path.replace('.mp3', '.wav')
        convert_mp3_to_wav(mp3_path, wav_path)
        print(f"Converted {filename} to WAV")
```

### Method 3: Professional Recording / Профессиональная запись

For highest quality, consider recording with a native Russian speaker:

1. **Equipment needed**:
   - USB microphone (e.g., Blue Yeti, Audio-Technica AT2020USB+)
   - Quiet recording environment
   - Audio recording software (Audacity - free, Adobe Audition - professional)

2. **Recording process**:
   - Record each phrase separately
   - Maintain consistent distance from microphone (6-8 inches)
   - Speak clearly and at moderate pace
   - Record 2-3 takes of each phrase
   - Select best take for each file

3. **Post-processing in Audacity**:
   - Remove background noise: Effect → Noise Reduction
   - Normalize volume: Effect → Normalize (-3dB)
   - Trim silence: Edit → Remove Audio → Trim Audio
   - Export as WAV: File → Export → Export as WAV

## Batch Generation Script / Скрипт пакетной генерации

A complete Python script for generating all audio files:

```python
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
"""

from gtts import gTTS
from pydub import AudioSegment
import os
from pathlib import Path

# Output directory
OUTPUT_DIR = Path('assets/audio')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
    """
    if n in RUSSIAN_NUMBERS:
        return RUSSIAN_NUMBERS[n]
    elif n < 100:
        tens = (n // 10) * 10
        ones = n % 10
        return f"{RUSSIAN_NUMBERS[tens]} {RUSSIAN_NUMBERS[ones]}"
    return str(n)

def generate_audio_file(text, filename, lang='ru'):
    """
    Generate audio file from text using gTTS and convert to WAV
    Генерировать аудио файл из текста используя gTTS и конвертировать в WAV
    
    Args:
        text: Text to convert to speech
        filename: Output filename (without extension)
        lang: Language code (default: 'ru' for Russian)
    """
    try:
        # Generate MP3 using gTTS
        mp3_path = OUTPUT_DIR / f"{filename}.mp3"
        wav_path = OUTPUT_DIR / f"{filename}.wav"
        
        print(f"Generating {filename}...")
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
        
        print(f"✓ Created {filename}.wav")
        return True
        
    except Exception as e:
        print(f"✗ Error generating {filename}: {e}")
        return False

def main():
    """
    Main function to generate all audio files
    Главная функция для генерации всех аудио файлов
    """
    print("=" * 60)
    print("RelayBot Audio File Generator")
    print("Генератор аудио файлов RelayBot")
    print("=" * 60)
    print()
    
    # Core system prompts
    print("Generating core system prompts...")
    print("Генерация основных системных подсказок...")
    print()
    
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
    print("Generating order number announcements (1-100)...")
    print("Генерация объявлений номеров заказов (1-100)...")
    print()
    
    order_success = 0
    for i in range(1, 101):
        text = f"Заказ номер {number_to_russian(i)}"
        filename = f"order_{i}"
        if generate_audio_file(text, filename):
            order_success += 1
        
        # Progress indicator
        if i % 10 == 0:
            print(f"Progress: {i}/100 files generated")
    
    print()
    print(f"Order numbers: {order_success}/100 generated")
    print()
    
    # Summary
    total_files = len(core_prompts) + 100
    total_success = success_count + order_success
    
    print("=" * 60)
    print("SUMMARY / ИТОГИ")
    print("=" * 60)
    print(f"Total files generated: {total_success}/{total_files}")
    print(f"Success rate: {(total_success/total_files)*100:.1f}%")
    print()
    print(f"Audio files location: {OUTPUT_DIR.absolute()}")
    print()
    
    if total_success == total_files:
        print("✓ All audio files generated successfully!")
        print("✓ Все аудио файлы успешно сгенерированы!")
    else:
        print("⚠ Some files failed to generate. Check errors above.")
        print("⚠ Некоторые файлы не удалось сгенерировать. Проверьте ошибки выше.")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
```

## Installation Instructions / Инструкции по установке

### Install Required Python Packages

```bash
pip install gtts pydub
```

### Install ffmpeg

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS**:
```bash
brew install ffmpeg
```

**Windows**:
1. Download ffmpeg from https://ffmpeg.org/download.html
2. Extract to C:\ffmpeg
3. Add C:\ffmpeg\bin to system PATH

### Run the Generation Script

```bash
# Save the script above as generate_audio_files.py
python generate_audio_files.py
```

## Verification / Проверка

After generating all audio files, verify they meet requirements:

После генерации всех аудио файлов, проверьте соответствие требованиям:

### Check File Count

```bash
# Should show 104 WAV files (4 core + 100 order numbers)
ls -1 assets/audio/*.wav | wc -l
```

### Check Audio Properties

```bash
# Install sox for audio analysis
sudo apt-get install sox

# Check single file properties
soxi assets/audio/request_qr.wav

# Expected output:
# Channels       : 1 (mono)
# Sample Rate    : 44100
# Precision      : 16-bit
# Duration       : ~3-4 seconds
```

### Test Playback

```python
from playsound3 import playsound

# Test core prompts
playsound('assets/audio/request_qr.wav')
playsound('assets/audio/order_accepted.wav')
playsound('assets/audio/order_rejected.wav')
playsound('assets/audio/delivery_greeting.wav')

# Test order numbers
playsound('assets/audio/order_1.wav')
playsound('assets/audio/order_50.wav')
playsound('assets/audio/order_100.wav')
```

## File Checklist / Контрольный список файлов

Use this checklist to ensure all files are created:

Используйте этот контрольный список для проверки создания всех файлов:

### Core System Prompts (4 files)
- [ ] request_qr.wav
- [ ] order_accepted.wav
- [ ] order_rejected.wav
- [ ] delivery_greeting.wav

### Order Numbers (100 files)
- [ ] order_1.wav through order_10.wav
- [ ] order_11.wav through order_20.wav
- [ ] order_21.wav through order_30.wav
- [ ] order_31.wav through order_40.wav
- [ ] order_41.wav through order_50.wav
- [ ] order_51.wav through order_60.wav
- [ ] order_61.wav through order_70.wav
- [ ] order_71.wav through order_80.wav
- [ ] order_81.wav through order_90.wav
- [ ] order_91.wav through order_100.wav

### Existing Files (2 files - move from assets/)
- [ ] successScan.wav (move from assets/ to assets/audio/)
- [ ] failureScan.wav (move from assets/ to assets/audio/)

**Total: 106 files**

## Troubleshooting / Устранение неполадок

### Issue: gTTS fails to generate audio
**Solution**: Check internet connection. gTTS requires internet to access Google's TTS API.

### Issue: pydub cannot find ffmpeg
**Solution**: Ensure ffmpeg is installed and in system PATH. Test with `ffmpeg -version`.

### Issue: Audio quality is poor
**Solution**: Consider using professional TTS services (Yandex SpeechKit, Google Cloud TTS) or recording with native speaker.

### Issue: Files are too large
**Solution**: Reduce sample rate to 22050 Hz or use mono instead of stereo.

### Issue: Audio is too quiet or too loud
**Solution**: Use audio normalization. In Audacity: Effect → Normalize to -3dB.

## Integration with RelayBot / Интеграция с RelayBot

Once all audio files are generated, the AudioSystem class in `audio_system.py` will automatically use them:

После генерации всех аудио файлов, класс AudioSystem в `audio_system.py` автоматически будет их использовать:

```python
from audio_system import AudioSystem

# Initialize audio system
audio = AudioSystem(audio_dir='assets/audio')

# Play prompts
audio.request_qr_code()  # Plays request_qr.wav
audio.announce_order_accepted()  # Plays order_accepted.wav
audio.announce_order_rejected()  # Plays order_rejected.wav
audio.greet_delivery()  # Plays delivery_greeting.wav

# Announce order number
audio.announce_order_number(42)  # Plays order_42.wav
```

## References / Ссылки

- **gTTS Documentation**: https://gtts.readthedocs.io/
- **pydub Documentation**: https://github.com/jiaaro/pydub
- **ffmpeg Documentation**: https://ffmpeg.org/documentation.html
- **Audacity**: https://www.audacityteam.org/
- **Yandex SpeechKit**: https://cloud.yandex.com/en/services/speechkit
- **Google Cloud TTS**: https://cloud.google.com/text-to-speech

## License / Лицензия

Audio files generated for RelayBot are for use within the RelayBot project only. If using third-party TTS services, ensure compliance with their terms of service.

Аудио файлы, сгенерированные для RelayBot, предназначены только для использования в проекте RelayBot. При использовании сторонних TTS сервисов убедитесь в соблюдении их условий использования.

---

**Last Updated**: 2024
**Version**: 1.0
**Author**: RelayBot Development Team
