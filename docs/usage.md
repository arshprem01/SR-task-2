# Usage Guide

## 1. Install prerequisites

Before running the app, install:

- Python 3.11+
- FFmpeg
- pip

See the main README for platform-specific guidance.

## 2. Create a virtual environment

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 4. Launch the application

```bash
streamlit run app.py
```

Then open the local URL shown in the terminal, typically http://localhost:8501.

## 5. Working with the interface

1. Upload a supported audio file.
2. Choose the model size and language.
3. Click Transcribe Audio.
4. Review the generated transcript.
5. Download the output as a text file or SRT subtitle file.

## 6. Supported audio

The app accepts:

- WAV
- MP3
- M4A
- FLAC
- OGG

## 7. Troubleshooting

### Model download fails

This usually means there is no internet access or the download is blocked. Confirm you have a working network connection and enough disk space.

### FFmpeg not found

Install FFmpeg and ensure it is on your PATH.

### File not accepted

Check that the file is not empty, corrupted, or in an unsupported format.

### Transcription is poor

Use a quality recording, reduce background noise, and select the nearest language/model size.
