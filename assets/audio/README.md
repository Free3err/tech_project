# RelayBot Audio Files / Аудио файлы RelayBot

This directory contains all audio files required for the RelayBot autonomous delivery system.

Эта директория содержит все аудио файлы, необходимые для автономной системы доставки RelayBot.

## Quick Start / Быстрый старт

### Generate Audio Files Automatically

```bash
# Install dependencies
pip install gtts pydub

# Install ffmpeg (if not already installed)
# Ubuntu/Debian: sudo apt-get install ffmpeg
# macOS: brew install ffmpeg

# Run the generator script
python generate_audio_files.py
```

This will create all 104 required audio files in this directory.

Это создаст все 104 необходимых аудио файла в этой директории.

## Required Files / Необходимые файлы

### Core System Prompts (4 files)

| File | Russian Text | English Translation | Usage |
|------|--------------|---------------------|-------|
| `request_qr.wav` | Пожалуйста, покажите QR код вашего заказа | Please show the QR code of your order | Request order verification |
| `order_accepted.wav` | Заказ принят. Еду на склад. | Order accepted. Going to the warehouse. | Order verified successfully |
| `order_rejected.wav` | Заказ не найден. Пожалуйста, проверьте QR код. | Order not found. Please check the QR code. | Order verification failed |
| `delivery_greeting.wav` | Ваш заказ доставлен. Приятного дня! | Your order has been delivered. Have a nice day! | Package delivery complete |

### Order Number Announcements (100 files)

- `order_1.wav` through `order_100.wav`
- Format: "Заказ номер [NUMBER]" (Order number [NUMBER])
- Used at warehouse loading zone to announce which order to load

### Existing Sound Effects (2 files)

- `successScan.wav` - QR code scan success sound
- `failureScan.wav` - QR code scan failure sound

**Note**: These files currently exist in the parent `assets/` directory and should be moved here.

## Audio Format Specifications / Спецификации формата аудио

All audio files must meet these specifications:

- **Format**: WAV (Waveform Audio File Format)
- **Sample Rate**: 44100 Hz (CD quality)
- **Bit Depth**: 16-bit
- **Channels**: Mono (1 channel)
- **Encoding**: PCM (Pulse Code Modulation)
- **Language**: Russian (Русский)
- **Volume**: Normalized to -3dB

## File Status / Статус файлов

Check which files are present:

```bash
# Count WAV files (should be 104 total)
ls -1 *.wav 2>/dev/null | wc -l

# List core prompts
ls -1 request_qr.wav order_accepted.wav order_rejected.wav delivery_greeting.wav 2>/dev/null

# List order numbers
ls -1 order_*.wav 2>/dev/null | head -10
```

## Testing Audio Files / Тестирование аудио файлов

### Test with Python

```python
from playsound3 import playsound

# Test core prompts
playsound('assets/audio/request_qr.wav')
playsound('assets/audio/order_accepted.wav')

# Test order numbers
playsound('assets/audio/order_1.wav')
playsound('assets/audio/order_50.wav')
```

### Test with Command Line

```bash
# Linux (using aplay)
aplay assets/audio/request_qr.wav

# macOS (using afplay)
afplay assets/audio/request_qr.wav

# Windows (using PowerShell)
(New-Object Media.SoundPlayer "assets\audio\request_qr.wav").PlaySync()
```

## Alternative Generation Methods / Альтернативные методы генерации

If the automatic script doesn't work, see `AUDIO_FILES_GUIDE.md` for:

- Online TTS services (Google Cloud, Yandex SpeechKit, Microsoft Azure)
- Manual recording instructions
- Professional recording setup
- Troubleshooting guide

## Integration with RelayBot / Интеграция с RelayBot

The `AudioSystem` class in `audio_system.py` automatically loads and plays these files:

```python
from audio_system import AudioSystem

audio = AudioSystem(audio_dir='assets/audio')

# Play prompts
audio.request_qr_code()           # Plays request_qr.wav
audio.announce_order_accepted()   # Plays order_accepted.wav
audio.announce_order_rejected()   # Plays order_rejected.wav
audio.greet_delivery()            # Plays delivery_greeting.wav

# Announce order number
audio.announce_order_number(42)   # Plays order_42.wav
```

## Requirements Mapping / Соответствие требованиям

These audio files satisfy the following requirements from the specification:

- **Requirement 13.1**: Audio feedback for order verification request
- **Requirement 13.2**: Audio feedback for order acceptance
- **Requirement 13.3**: Audio feedback for order rejection
- **Requirement 13.4**: Audio announcement of order number at warehouse
- **Requirement 13.5**: Audio greeting for delivery completion

## Documentation / Документация

For complete documentation, see:

- `AUDIO_FILES_GUIDE.md` - Comprehensive guide with all generation methods
- `../../../.kiro/specs/relaybot-autonomous-delivery/requirements.md` - System requirements
- `../../../.kiro/specs/relaybot-autonomous-delivery/design.md` - Audio system design

## Support / Поддержка

If you encounter issues generating audio files:

1. Check that all dependencies are installed (gtts, pydub, ffmpeg)
2. Verify internet connection (gTTS requires internet)
3. Review error messages in the generation script output
4. Consult `AUDIO_FILES_GUIDE.md` for troubleshooting
5. Consider using alternative TTS services or professional recording

---

**Last Updated**: 2024  
**Version**: 1.0  
**Related Files**: `audio_system.py`, `generate_audio_files.py`
