from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from asr.audio_utils import generate_srt, validate_audio_file
from asr.transcriber import Transcriber

MODEL_OPTIONS = ["tiny", "base", "small", "medium", "large-v3", "large-v3-turbo"]
LANGUAGE_OPTIONS = ["auto", "en", "fr", "es", "de", "it", "pt", "zh", "ja", "ko", "hi", "ar", "ru"]


st.set_page_config(page_title="ASR Tool", page_icon="🎙️", layout="wide")


@st.cache_resource
def get_transcriber(model_size: str) -> Transcriber:
    return Transcriber(model_size=model_size)


def clear_session() -> None:
    for key in ["uploaded_audio", "audio_path", "transcript_result", "transcription_text"]:
        st.session_state.pop(key, None)


def write_safely(text: str) -> str:
    return text.strip() or "No transcription available yet."


def save_uploaded_audio(uploaded_file) -> str:
    suffix = Path(getattr(uploaded_file, "name", "audio.wav")).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(uploaded_file.getvalue())
        temp_path = temp_file.name
    return temp_path


def main() -> None:
    st.title("ASR Tool — Speech-to-Text Transcription System")
    st.caption("Upload a short audio clip, choose the model and language, and generate a transcript in seconds.")
    st.markdown(
        "This app uses a pretrained Whisper-based transcription model to convert spoken audio into readable text. "
        "Audio quality, accent, language, and model size affect the quality of results."
    )

    uploaded_file = st.file_uploader(
        "Upload an audio file",
        type=["wav", "mp3", "m4a", "flac", "ogg"],
        help="Supported formats: WAV, MP3, M4A, FLAC, and OGG.",
    )

    col1, col2 = st.columns(2)
    with col1:
        model_size = st.selectbox("Model size", MODEL_OPTIONS, index=1)
    with col2:
        language = st.selectbox("Language", LANGUAGE_OPTIONS, index=0)

    if uploaded_file is not None:
        st.session_state["uploaded_audio"] = uploaded_file
        st.info(f"Filename: {uploaded_file.name} | Size: {uploaded_file.size / 1024:.1f} KB")

        try:
            temp_path = save_uploaded_audio(uploaded_file)
            validate_audio_file(temp_path)
            st.session_state["audio_path"] = temp_path
            st.audio(temp_path, format="audio/wav")
        except (FileNotFoundError, ValueError) as exc:
            st.error(str(exc))
            st.session_state.pop("audio_path", None)
            return

    transcribe_button = st.button("Transcribe Audio", type="primary")
    clear_button = st.button("Clear")

    if clear_button:
        clear_session()
        st.rerun()

    if not transcribe_button:
        return

    audio_path = st.session_state.get("audio_path")
    if not audio_path:
        st.warning("Please upload a valid audio file before transcribing.")
        return

    try:
        transcriber = get_transcriber(model_size)
        with st.spinner("Transcribing audio... this can take a few moments."):
            result = transcriber.transcribe(audio_path, language=language)
        st.session_state["transcript_result"] = result
        st.success("Transcription complete.")
    except Exception as exc:  # pragma: no cover - UI safety net
        st.error(f"Transcription failed: {exc}")
        return

    transcript = write_safely(result["text"])
    st.session_state["transcription_text"] = transcript

    st.subheader("Transcription Output")
    st.text_area(
        "Full transcript",
        value=transcript,
        height=250,
        key="transcription_box",
    )

    st.markdown(f"Detected language: **{result.get('language', 'unknown')}**")
    st.markdown(f"Processing time: **{result.get('processing_time', 0.0):.2f} seconds**")
    st.markdown(f"Audio duration: **{result.get('duration', 0.0):.2f} seconds**")

    col_download_txt, col_download_srt = st.columns(2)
    with col_download_txt:
        st.download_button(
            label="Download transcript (.txt)",
            data=transcript,
            file_name="transcript.txt",
            mime="text/plain",
        )
    with col_download_srt:
        srt_data = generate_srt(result.get("segments", []))
        st.download_button(
            label="Download subtitles (.srt)",
            data=srt_data,
            file_name="transcript.srt",
            mime="text/plain",
        )

    with st.expander("View timestamped segments"):
        for segment in result.get("segments", []):
            st.write(f"{segment.get('start', 0.0):.2f}s - {segment.get('end', 0.0):.2f}s: {segment.get('text', '')}")

    st.markdown("### About this model")
    st.markdown(
        "The application uses OpenAI Whisper via the faster-whisper library for efficient CPU-based transcription. "
        "The model is selected by the user, and it is capable of handling English and other supported languages."
    )


if __name__ == "__main__":
    main()
