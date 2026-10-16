from __future__ import annotations

import json
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any

SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}


def is_supported_audio_extension(filename: str | None) -> bool:
    """Return True when the file extension is in the supported audio set."""
    if not filename:
        return False
    return Path(filename).suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS


def format_timestamp(seconds: float) -> str:
    """Format a timestamp in HH:MM:SS,mmm format for subtitles and display."""
    total_ms = max(0, round(float(seconds) * 1000))
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


def get_audio_metadata(file_path: str | Path) -> dict[str, Any]:
    """Read basic duration and stream details with ffprobe when available."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_name,sample_rate,channels,codec_type",
            "-of",
            "json",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError("Unable to read audio metadata.")
    try:
        metadata = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("Unable to read audio metadata.") from exc

    audio_stream = next(
        (stream for stream in metadata.get("streams", []) if stream.get("codec_type") == "audio"),
        {},
    )
    format_data = metadata.get("format", {})
    duration = format_data.get("duration")
    return {
        "duration": float(duration) if duration is not None else None,
        "codec": audio_stream.get("codec_name"),
        "sample_rate": audio_stream.get("sample_rate"),
        "channels": audio_stream.get("channels"),
    }


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

    try:
        ffmpeg = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError("FFmpeg is required to validate uploaded audio. Install FFmpeg and make it available on PATH.") from exc
    if ffmpeg.returncode != 0:
        raise ValueError("Invalid audio file: ffmpeg could not decode the uploaded file.")

    return path
