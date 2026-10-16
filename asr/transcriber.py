from __future__ import annotations

import re
from pathlib import Path
from time import perf_counter
from typing import Any

from .audio_utils import generate_srt, validate_audio_file

try:
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover - handled at runtime
    WhisperModel = None

SUPPORTED_MODELS = {
    "tiny",
    "base",
    "small",
    "medium",
    "large",
    "large-v2",
    "large-v3",
    "large-v3-turbo",
}

SUPPORTED_LANGUAGES = {
    "auto",
    "en",
    "fr",
    "es",
    "de",
    "it",
    "pt",
    "zh",
    "ja",
    "ko",
    "hi",
    "ar",
    "ru",
    "tr",
    "pl",
    "nl",
    "sv",
    "uk",
    "fi",
    "cs",
    "ro",
    "hu",
    "el",
    "th",
    "id",
    "ms",
    "vi",
    "he",
    "fa",
    "bn",
    "ta",
    "te",
    "ml",
    "kn",
    "mr",
    "gu",
    "pa",
    "ur",
    "am",
    "km",
    "lo",
    "my",
    "ne",
    "sk",
    "sl",
    "lt",
    "lv",
    "et",
    "ca",
    "sr",
    "hr",
    "bg",
    "da",
    "no",
    "is",
    "eu",
    "gl",
    "sw",
}


def validate_model_size(model_name: str) -> bool:
    return model_name in SUPPORTED_MODELS


def validate_language(language: str | None) -> bool:
    if language is None:
        return False
    return language.lower() in SUPPORTED_LANGUAGES


def format_transcription(text: str | None) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"\s+([,.;:?!])", r"\1", cleaned)
    return cleaned


class Transcriber:
    """Thin wrapper around faster-whisper with a simple API for the app."""

    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8") -> None:
        if not validate_model_size(model_size):
            raise ValueError(f"Unsupported model size '{model_size}'. Choose one of: {sorted(SUPPORTED_MODELS)}")
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None

    def _load_model(self):
        if self.model is not None:
            return self.model
        if WhisperModel is None:
            raise RuntimeError("The 'faster-whisper' dependency is not installed. Install requirements first.")
        self.model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )
        return self.model

    def transcribe(self, audio_path: str | Path, language: str = "auto", task: str = "transcribe") -> dict[str, Any]:
        path = Path(audio_path)
        if not path.exists():
            raise ValueError(f"Audio file does not exist or is empty: {path}")

        validate_audio_file(path)

        start_time = perf_counter()
        try:
            model = self._load_model()
            transcription_kwargs: dict[str, Any] = {"task": task, "beam_size": 5, "word_timestamps": False}
            if language and language.lower() != "auto":
                transcription_kwargs["language"] = language

            raw_result = model.transcribe(str(path), **transcription_kwargs)
        except Exception as exc:  # noqa: BLE001 - app converts to friendly message later
            raise ValueError(f"Transcription failed: {exc}") from exc

        if isinstance(raw_result, tuple) and len(raw_result) == 2:
            segments, info = raw_result
            detected_language = getattr(info, "language", None) or "auto"
        elif isinstance(raw_result, list):
            segments = raw_result
            detected_language = getattr(raw_result[0], "language", "auto") if raw_result else "auto"
        else:
            raise ValueError("The transcription engine did not return a valid result.")

        formatted_segments: list[dict[str, Any]] = []
        for segment in segments:
            segment_text = format_transcription(getattr(segment, "text", ""))
            if not segment_text:
                continue
            formatted_segments.append(
                {
                    "start": float(getattr(segment, "start", 0.0) or 0.0),
                    "end": float(getattr(segment, "end", 0.0) or 0.0),
                    "text": segment_text,
                    "language": getattr(segment, "language", detected_language),
                }
            )

        transcript_text = " ".join(segment["text"] for segment in formatted_segments)
        processing_time = perf_counter() - start_time

        if not transcript_text.strip():
            raise ValueError("The model produced no transcription. Please try a clearer or longer recording.")

        return {
            "text": transcript_text,
            "language": detected_language if detected_language != "auto" else "auto",
            "segments": formatted_segments,
            "duration": max((segment["end"] for segment in formatted_segments), default=0.0),
            "processing_time": round(processing_time, 2),
            "srt": generate_srt(formatted_segments),
        }
