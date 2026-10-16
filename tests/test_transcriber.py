from pathlib import Path
from types import SimpleNamespace

import pytest

from asr.transcriber import (
    Transcriber,
    format_transcription,
    validate_language,
    validate_model_size,
)


@pytest.mark.parametrize(
    "model_name, expected",
    [
        ("tiny", True),
        ("base", True),
        ("small", True),
        ("medium", True),
        ("large-v3", True),
        ("invalid-model", False),
    ],
)
def test_model_configuration_validation(model_name, expected):
    assert validate_model_size(model_name) is expected


@pytest.mark.parametrize(
    "language, expected",
    [
        ("auto", True),
        ("en", True),
        ("fr", True),
        ("zh", True),
        ("invalid-lang", False),
    ],
)
def test_language_validation(language, expected):
    assert validate_language(language) is expected


def test_transcription_output_formatting():
    result = "  Hello   world!\n\nThis is a test.  "
    cleaned = format_transcription(result)

    assert "Hello world!" in cleaned
    assert "This is a test." in cleaned
    assert "\n\n" not in cleaned.strip()


def test_error_handling_when_transcription_fails():
    transcriber = Transcriber()

    with pytest.raises(ValueError, match="Audio file.*missing|empty|does not exist"):
        transcriber.transcribe("/tmp/does-not-exist.wav")


def test_mocked_transcription_run(tmp_path, monkeypatch):
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"dummy")

    fake_model = SimpleNamespace(
        transcribe=lambda *args, **kwargs: [
            SimpleNamespace(
                text="Hello there",
                language="en",
                start=0.0,
                end=1.5,
            )
        ]
    )

    monkeypatch.setattr("asr.transcriber.WhisperModel", lambda *args, **kwargs: fake_model)
    monkeypatch.setattr("asr.transcriber.validate_audio_file", lambda *args, **kwargs: Path(audio_path))
    transcriber = Transcriber(model_size="tiny")
    output = transcriber.transcribe(audio_path)

    assert output["text"] == "Hello there"
    assert output["language"] == "en"
    assert output["segments"][0]["text"] == "Hello there"


def test_transcriber_rejects_invalid_language(tmp_path, monkeypatch):
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"dummy")
    monkeypatch.setattr("asr.transcriber.validate_audio_file", lambda *args, **kwargs: Path(audio_path))

    with pytest.raises(ValueError, match="Unsupported language code"):
        Transcriber(model_size="tiny").transcribe(audio_path, language="invalid-lang")
