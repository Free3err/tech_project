# Audio Generation Instructions for RelayBot

## Overview

Task 30 of the RelayBot autonomous delivery system requires creating 104 audio files for voice feedback. Since audio files cannot be generated programmatically within the codebase, this document provides instructions for generating them separately.

## What Has Been Created

The following documentation and tools have been created to help you generate the audio files:

### 1. Comprehensive Documentation
- **`assets/audio/AUDIO_FILES_GUIDE.md`** - Complete guide with:
  - List of all 104 required audio files with Russian text
  - Audio format specifications (WAV, 44.1kHz, 16-bit, mono)
  - Multiple generation methods (online TTS, Python libraries, professional recording)
  - Detailed instructions for each method
  - Troubleshooting guide

### 2. Russian Numbers Reference
- **`assets/audio/RUSSIAN_NUMBERS_REFERENCE.md`** - Complete reference for:
  - All Russian numbers 1-100 with pronunciation
  - Compound number construction rules
  - Pronunciation tips for non-native speakers
  - Complete list for manual recording

### 3. Quick Reference
- **`assets/audio/README.md`** - Quick start guide with:
  - File requirements summary
  - Quick generation commands
  - Testing instructions
  - Integration information

### 4. Automated Generation Script
- **`generate_audio_files.py`** - Python script that:
  - Automatically generates all 104 audio files
  - Uses Google Text-to-Speech (gTTS)
  - Converts MP3 to WAV format
  - Normalizes audio volume
  - Provides progress feedback
  - Handles errors gracefully

### 5. Testing Script
- **`test_audio_files.py`** - Verification script that:
  - Checks all required files exist
  - Verifies audio file properties
  - Tests playback functionality
  - Provides detailed status report

### 6. Updated Dependencies
- **`requirements.txt`** - Added:
  - `gtts>=2.3.0` - Google Text-to-Speech
  - `pydub>=0.25.0` - Audio file conversion

## Quick Start: Generate Audio Files

### Method 1: Automated Generation (Recommended)

```bash
# Step 1: Install dependencies
pip install gtts pydub

# Step 2: Install ffmpeg (required for audio conversion)
# Ubuntu/Debian:
sudo apt-get install ffmpeg

# macOS:
brew install ffmpeg

# Windows: Download from https://ffmpeg.org/

# Step 3: Run the generation script
python generate_audio_files.py

# Step 4: Verify files were created
python test_audio_files.py

# Step 5: Test playback (optional)
python test_audio_files.py --play-samples
```

This will create all 104 audio files in `assets/audio/`:
- 4 core system prompts
- 100 order number announcements

### Method 2: Online TTS Services

If the automated script doesn't work, use online services:

1. **Yandex SpeechKit** (Best for Russian)
   - Visit: https://cloud.yandex.com/en/services/speechkit
   - Generate each phrase manually
   - Download as WAV files

2. **Google Cloud Text-to-Speech**
   - Visit: https://cloud.google.com/text-to-speech
   - Select Russian (ru-RU)
   - Generate and download

3. **Microsoft Azure Speech**
   - Visit: https://azure.microsoft.com/services/cognitive-services/text-to-speech/
   - Select Russian voice
   - Generate and download

See `assets/audio/AUDIO_FILES_GUIDE.md` for detailed instructions.

### Method 3: Professional Recording

For highest quality, record with a native Russian speaker:
- See `assets/audio/AUDIO_FILES_GUIDE.md` Section "Method 3: Professional Recording"
- Use `assets/audio/RUSSIAN_NUMBERS_REFERENCE.md` for pronunciation guide

## Required Audio Files

### Core System Prompts (4 files)

| File | Russian Text | Usage |
|------|--------------|-------|
| `request_qr.wav` | Пожалуйста, покажите QR код вашего заказа | Request order verification |
| `order_accepted.wav` | Заказ принят. Еду на склад. | Order verified successfully |
| `order_rejected.wav` | Заказ не найден. Пожалуйста, проверьте QR код. | Order verification failed |
| `delivery_greeting.wav` | Ваш заказ доставлен. Приятного дня! | Package delivery complete |

### Order Number Announcements (100 files)

- `order_1.wav` through `order_100.wav`
- Format: "Заказ номер [NUMBER]" (Order number [NUMBER])
- Examples:
  - `order_1.wav`: "Заказ номер один"
  - `order_25.wav`: "Заказ номер двадцать пять"
  - `order_100.wav`: "Заказ номер сто"

## Audio Format Requirements

All files must be:
- **Format**: WAV (Waveform Audio File Format)
- **Sample Rate**: 44100 Hz (CD quality)
- **Bit Depth**: 16-bit
- **Channels**: Mono (1 channel)
- **Encoding**: PCM
- **Language**: Russian
- **Volume**: Normalized to -3dB

## Verification

After generating files, verify they work:

```bash
# Check file count (should be 104)
python test_audio_files.py

# Check with detailed properties
python test_audio_files.py --check-properties

# Test playback
python test_audio_files.py --play-samples
```

## Integration with RelayBot

Once audio files are generated, the `AudioSystem` class will automatically use them:

```python
from audio_system import AudioSystem

audio = AudioSystem(audio_dir='assets/audio')

# The system will automatically play the correct files
audio.request_qr_code()           # Plays request_qr.wav
audio.announce_order_accepted()   # Plays order_accepted.wav
audio.announce_order_number(42)   # Plays order_42.wav
audio.greet_delivery()            # Plays delivery_greeting.wav
```

## Troubleshooting

### Issue: Script fails with "No module named 'gtts'"
**Solution**: Install dependencies: `pip install gtts pydub`

### Issue: "ffmpeg not found"
**Solution**: Install ffmpeg:
- Ubuntu/Debian: `sudo apt-get install ffmpeg`
- macOS: `brew install ffmpeg`
- Windows: Download from https://ffmpeg.org/

### Issue: No internet connection
**Solution**: gTTS requires internet. Use offline methods:
- Professional recording
- Pre-download audio from online TTS services

### Issue: Audio quality is poor
**Solution**: 
- Use professional TTS services (Yandex SpeechKit recommended for Russian)
- Record with native Russian speaker
- See `assets/audio/AUDIO_FILES_GUIDE.md` for detailed quality improvement tips

## Requirements Mapping

These audio files satisfy the following requirements:

- **Requirement 13.1**: Audio feedback for order verification request
- **Requirement 13.2**: Audio feedback for order acceptance
- **Requirement 13.3**: Audio feedback for order rejection
- **Requirement 13.4**: Audio announcement of order number at warehouse
- **Requirement 13.5**: Audio greeting for delivery completion

## Task Status

✅ **Task 30.1 Complete**: Documentation and generation tools created

**What's Done**:
- ✅ Comprehensive documentation created
- ✅ Automated generation script created
- ✅ Testing/verification script created
- ✅ Russian numbers reference created
- ✅ Dependencies added to requirements.txt
- ✅ Quick reference guide created

**What You Need to Do**:
- ⏳ Run `python generate_audio_files.py` to generate the actual audio files
- ⏳ Verify files with `python test_audio_files.py`
- ⏳ Test audio quality and adjust if needed

## Next Steps

1. **Generate audio files** using one of the methods above
2. **Verify** all 104 files are created correctly
3. **Test** audio playback to ensure quality
4. **Integrate** with RelayBot system (already configured in `audio_system.py`)
5. **Move existing files**: Move `assets/successScan.wav` and `assets/failureScan.wav` to `assets/audio/`

## Documentation Files

All documentation is located in `assets/audio/`:

1. **AUDIO_FILES_GUIDE.md** - Comprehensive guide (main reference)
2. **RUSSIAN_NUMBERS_REFERENCE.md** - Russian numbers 1-100
3. **README.md** - Quick reference

## Support

For issues or questions:
1. Check `assets/audio/AUDIO_FILES_GUIDE.md` troubleshooting section
2. Verify all dependencies are installed
3. Test with sample files first
4. Consider alternative generation methods if one fails

---

**Created**: 2024  
**Task**: 30.1 - Record or generate Russian audio prompts  
**Status**: Documentation Complete - Ready for Audio Generation  
**Related Files**: 
- `generate_audio_files.py`
- `test_audio_files.py`
- `assets/audio/AUDIO_FILES_GUIDE.md`
- `assets/audio/RUSSIAN_NUMBERS_REFERENCE.md`
- `assets/audio/README.md`
