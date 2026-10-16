from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Iterable

SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}


def is_supported_audio_extension(filename: str | None) -> bool:
    """Return True when the file extension is in the supported audio set."""
    if not filename:
        return False
    return Path(filename).suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS


def format_timestamp(seconds: float) -> str:
    """Format a timestamp in HH:MM:SS,mmm format for subtitles and display."""
    total_ms = max(0, int(round(float(seconds) * 1000)))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def generate_srt(segments: Iterable[dict[str, Any]]) -> str:
    """Generate a subtitle file from a list of timestamped transcription segments."""
    lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        lines.append(str(index))
        lines.append(f"{format_timestamp(start)} --> {format_timestamp(end)}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).rstrip() + ("\n" if lines else "")


def validate_audio_file(file_path: Any, max_size_mb: float = 25.0) -> Path:
    """Validate the presence, extension, size, and usability of a candidate audio file."""
    if file_path is None:
        raise ValueError("The uploaded audio file is empty or invalid.")

    if hasattr(file_path, "read"):
        uploaded = file_path
        name = getattr(uploaded, "name", "")
        if not name:
            raise ValueError("The uploaded audio file is empty or invalid.")
        if not is_supported_audio_extension(name):
            raise ValueError(
                "Unsupported audio format. Please upload a .wav, .mp3, .m4a, .flac, or .ogg file."
            )
        data = uploaded.read()
        if not data:
            raise ValueError("The uploaded audio file is empty or invalid.")
        if len(data) > max_size_mb * 1024 * 1024:
            raise ValueError("Invalid audio file: file size exceeds the allowed limit.")
        return Path(name)

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file does not exist: {path}")
    if path.is_dir():
        raise ValueError("Invalid audio file: the selected path points to a directory.")
    if path.stat().st_size == 0:
        raise ValueError("The uploaded audio file is empty or invalid.")
    if not is_supported_audio_extension(str(path)):
        raise ValueError(
            "Unsupported audio format. Please upload a .wav, .mp3, .m4a, .flac, or .ogg file."
        )
    if path.stat().st_size > max_size_mb * 1024 * 1024:
        raise ValueError("Invalid audio file: file size exceeds the allowed limit.")

    ffmpeg = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if ffmpeg.returncode != 0:
        raise ValueError("Invalid audio file: ffmpeg could not decode the uploaded file.")

    return path
