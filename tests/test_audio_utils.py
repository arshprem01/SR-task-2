from pathlib import Path

import pytest

from asr.audio_utils import (
    format_timestamp,
    generate_srt,
    is_supported_audio_extension,
    validate_audio_file,
)


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("sample.wav", True),
        ("sample.mp3", True),
        ("sample.m4a", True),
        ("sample.flac", True),
        ("sample.ogg", True),
        ("sample.txt", False),
        ("sample.mp4", False),
    ],
)
def test_supported_and_unsupported_extensions(filename, expected):
    assert is_supported_audio_extension(filename) is expected


def test_invalid_or_empty_uploads(tmp_path):
    empty_file = tmp_path / "empty.wav"
    empty_file.write_bytes(b"")

    with pytest.raises(ValueError, match="empty|empty file|not valid"):
        validate_audio_file(empty_file, max_size_mb=20)

    invalid_path = tmp_path / "missing.wav"
    with pytest.raises(FileNotFoundError):
        validate_audio_file(invalid_path, max_size_mb=20)


def test_audio_validation_utilities(tmp_path):
    valid_file = tmp_path / "valid.wav"
    valid_file.write_bytes(b"RIFF" + b"\x00" * 10)

    with pytest.raises(ValueError, match="(?i)unsupported|missing|invalid"):
        validate_audio_file(valid_file, max_size_mb=0.001)

    assert format_timestamp(61.2) == "00:01:01,200"


def test_srt_generation_for_segments():
    segments = [
        {"start": 0.0, "end": 1.5, "text": "Hello world"},
        {"start": 1.5, "end": 3.0, "text": "Second line"},
    ]

    srt = generate_srt(segments)

    assert "1" in srt
    assert "00:00:00,000 --> 00:00:01,500" in srt
    assert "Hello world" in srt
    assert "Second line" in srt
