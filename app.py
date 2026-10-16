from __future__ import annotations

import hashlib
import logging
import mimetypes
import tempfile
from pathlib import Path

import streamlit as st

from asr.audio_utils import (
    format_timestamp,
    generate_srt,
    get_audio_metadata,
    is_supported_audio_extension,
    validate_audio_file,
)
from asr.transcriber import Transcriber

LOGGER = logging.getLogger(__name__)
MAX_UPLOAD_SIZE_MB = 25
MODEL_OPTIONS = ["tiny", "base", "small", "medium", "large-v3", "large-v3-turbo"]
MODEL_HELP = {
    "tiny": "Fastest and lightest; useful for a quick draft.",
    "base": "Recommended starting point for CPU transcription.",
    "small": "A balance of accuracy and speed; uses more memory.",
    "medium": "Higher accuracy, but slower and more memory intensive.",
    "large-v3": "Best quality for many languages; requires substantial memory.",
    "large-v3-turbo": "Large-model quality with faster inference on supported setups.",
}
LANGUAGE_OPTIONS = {
    "Automatic detection": "auto",
    "English": "en",
    "Arabic": "ar",
    "Bengali": "bn",
    "Chinese": "zh",
    "Dutch": "nl",
    "French": "fr",
    "German": "de",
    "Greek": "el",
    "Hindi": "hi",
    "Indonesian": "id",
    "Italian": "it",
    "Japanese": "ja",
    "Korean": "ko",
    "Persian": "fa",
    "Polish": "pl",
    "Portuguese": "pt",
    "Russian": "ru",
    "Spanish": "es",
    "Swahili": "sw",
    "Tamil": "ta",
    "Telugu": "te",
    "Thai": "th",
    "Turkish": "tr",
    "Ukrainian": "uk",
    "Urdu": "ur",
    "Vietnamese": "vi",
}


st.set_page_config(page_title="Vox | Speech to Text", page_icon="🎙️", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
    :root { --ink: #18352f; --muted: #64736e; --paper: #f5f7f3; --line: #dce5dd; --green: #176b52; --lime: #d9ed83; }
    .stApp { background: var(--paper); color: var(--ink); font-family: 'DM Sans', sans-serif; }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1160px; padding-top: 2.1rem; padding-bottom: 3rem; }
    h1, h2, h3 { font-family: 'Manrope', sans-serif !important; color: var(--ink) !important; letter-spacing: 0 !important; }
    .brandline { display:flex; align-items:center; gap:.65rem; margin-bottom:1.3rem; color:var(--green); font-size:.76rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }
    .brandmark { display:grid; place-items:center; width:2rem; height:2rem; border-radius:9px; background:var(--lime); color:var(--ink); font-size:1rem; }
    .lede { max-width:680px; color:var(--muted); font-size:1.04rem; line-height:1.65; margin-top:-.45rem; }
    .eyebrow { color:var(--green); font-size:.74rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; margin:0 0 .35rem; }
    div[data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line); border-radius:12px; background:#fff; }
    div[data-testid="stFileUploader"] section { border:1px dashed #9cb9aa; border-radius:10px; background:#f8fbf7; }
    div[data-testid="stFileUploader"] section:hover { border-color:var(--green); }
    .stButton > button, .stDownloadButton > button { min-height:2.65rem; border-radius:8px; font-weight:700; }
    .stButton > button[kind="primary"] { background:var(--green); border-color:var(--green); color:#fff; }
    .stButton > button[kind="primary"]:hover { background:#10563f; border-color:#10563f; }
    .stDownloadButton > button { border-color:var(--line); color:var(--ink); background:#fff; }
    div[data-testid="stMetric"] { background:#f7faf6; border:1px solid var(--line); padding:.7rem .85rem; border-radius:8px; }
    div[data-testid="stMetricLabel"] { color:var(--muted); }
    .subtle { color:var(--muted); font-size:.88rem; }
    @media (max-width: 720px) { .block-container { padding:1.1rem 1rem 2rem; } .lede { font-size:.96rem; } }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_transcriber(model_size: str) -> Transcriber:
    return Transcriber(model_size=model_size)


def remove_temp_audio() -> None:
    audio_path = st.session_state.pop("audio_path", None)
    if audio_path:
        Path(audio_path).unlink(missing_ok=True)
    st.session_state.pop("audio_signature", None)
    st.session_state.pop("audio_metadata", None)


def clear_session() -> None:
    remove_temp_audio()
    for key in ["transcript_result", "result_signature"]:
        st.session_state.pop(key, None)
    st.session_state["uploader_version"] = st.session_state.get("uploader_version", 0) + 1


def save_uploaded_audio(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(uploaded_file.getvalue())
        return temp_file.name


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def render_transcript(result: dict, signature: str) -> None:
    if result.get("text") is None:
        return

    st.markdown("### Transcript")
    metrics = st.columns(3)
    metrics[0].metric("Detected language", result.get("language", "unknown").upper())
    metrics[1].metric("Audio length", format_timestamp(result.get("duration", 0)).replace(",", "."))
    metrics[2].metric("Processing", f"{result.get('processing_time', 0.0):.1f} sec")

    st.text_area(
        "Transcript text",
        value=result["text"],
        height=220,
        key=f"transcript_{signature[:12]}",
        help="Select and copy text directly, or use the download buttons below.",
    )
    downloads = st.columns([1, 1, 3])
    downloads[0].download_button(
        "Download .txt",
        data=result["text"],
        file_name="transcript.txt",
        mime="text/plain; charset=utf-8",
        icon="⬇️",
        key=f"txt_{signature[:12]}",
    )
    downloads[1].download_button(
        "Download .srt",
        data=generate_srt(result.get("segments", [])),
        file_name="transcript.srt",
        mime="text/plain; charset=utf-8",
        icon="⬇️",
        key=f"srt_{signature[:12]}",
    )

    segments = result.get("segments", [])
    if segments:
        with st.expander(f"Timestamped segments · {len(segments)}"):
            for segment in segments:
                start = format_timestamp(segment.get("start", 0)).replace(",", ".")
                end = format_timestamp(segment.get("end", 0)).replace(",", ".")
                st.markdown(f"`{start} – {end}`　{segment.get('text', '')}")


def main() -> None:
    st.markdown('<div class="brandline"><span class="brandmark">V</span> VOX · LOCAL TRANSCRIPTION</div>', unsafe_allow_html=True)
    st.title("Turn audio into clear text.")
    st.markdown(
        '<p class="lede">A private, on-device workspace for speech transcription. Drop in a recording, choose how it should be read, and export a transcript or timed subtitles.</p>',
        unsafe_allow_html=True,
    )

    upload_col, settings_col = st.columns([1.4, 0.8], gap="large")
    with upload_col, st.container(border=True):
        st.markdown('<p class="eyebrow">01 / Source audio</p>', unsafe_allow_html=True)
        st.subheader("Add a recording")
        st.caption("WAV, MP3, M4A, FLAC or OGG · up to 25 MB")
        uploader_version = st.session_state.get("uploader_version", 0)
        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=["wav", "mp3", "m4a", "flac", "ogg"],
            label_visibility="collapsed",
            help="Your audio stays on this machine while it is transcribed.",
            key=f"audio_uploader_{uploader_version}",
        )

        audio_path = None
        audio_signature = None
        if uploaded_file is not None:
            audio_data = uploaded_file.getvalue()
            audio_signature = hashlib.sha256(audio_data).hexdigest()
            if uploaded_file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                st.error(f"This file is over the {MAX_UPLOAD_SIZE_MB} MB upload limit.")
                remove_temp_audio()
            elif not is_supported_audio_extension(uploaded_file.name):
                st.error("That file type is not supported. Choose WAV, MP3, M4A, FLAC or OGG.")
                remove_temp_audio()
            else:
                if st.session_state.get("audio_signature") != audio_signature:
                    remove_temp_audio()
                    audio_path = save_uploaded_audio(uploaded_file)
                    st.session_state["audio_path"] = audio_path
                    st.session_state["audio_signature"] = audio_signature
                    st.session_state.pop("transcript_result", None)
                    st.session_state.pop("result_signature", None)
                    try:
                        validate_audio_file(audio_path, max_size_mb=MAX_UPLOAD_SIZE_MB)
                        st.session_state["audio_metadata"] = get_audio_metadata(audio_path)
                    except (OSError, RuntimeError, ValueError) as exc:
                        remove_temp_audio()
                        st.error(str(exc) if isinstance(exc, (RuntimeError, ValueError)) else "Unable to read the uploaded audio file.")
                        return
                else:
                    audio_path = st.session_state.get("audio_path")

                st.audio(audio_data, format=uploaded_file.type or mimetypes.guess_type(uploaded_file.name)[0])
                metadata = st.session_state.get("audio_metadata", {})
                file_details = [uploaded_file.name, format_file_size(uploaded_file.size)]
                if metadata.get("duration") is not None:
                    file_details.append(f"{metadata['duration']:.1f} sec")
                if metadata.get("codec"):
                    file_details.append(metadata["codec"].upper())
                st.markdown(f'<p class="subtle">{"　·　".join(file_details)}</p>', unsafe_allow_html=True)

    with settings_col, st.container(border=True):
        st.markdown('<p class="eyebrow">02 / Transcription</p>', unsafe_allow_html=True)
        st.subheader("Choose settings")
        model_size = st.selectbox("Model", MODEL_OPTIONS, index=1, help=MODEL_HELP)
        language_label = st.selectbox("Spoken language", list(LANGUAGE_OPTIONS), index=0)
        language = LANGUAGE_OPTIONS[language_label]
        st.caption(f"{MODEL_HELP[model_size]} Models download on first use; internet is required for that download.")
        transcribe_button = st.button(
            "Transcribe audio",
            type="primary",
            icon=":material/graphic_eq:",
            use_container_width=True,
            disabled=not bool(st.session_state.get("audio_path")),
        )
        clear_button = st.button("Clear workspace", icon=":material/delete_sweep:", use_container_width=True)

    if clear_button:
        clear_session()
        st.rerun()

    current_signature = f"{st.session_state.get('audio_signature', '')}:{model_size}:{language}"
    if transcribe_button:
        audio_path = st.session_state.get("audio_path")
        if not audio_path:
            st.warning("Choose a valid audio file before transcribing.")
        else:
            try:
                with st.spinner("Loading the model and transcribing your recording…"):
                    result = get_transcriber(model_size).transcribe(audio_path, language=language)
                st.session_state["transcript_result"] = result
                st.session_state["result_signature"] = current_signature
                st.toast("Transcription complete", icon="✅")
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                LOGGER.exception("Unexpected transcription error")
                st.error("Transcription could not be completed. Check the model download, available memory, and FFmpeg setup, then try again.")

    st.divider()
    result = st.session_state.get("transcript_result")
    if result and st.session_state.get("result_signature") == current_signature:
        render_transcript(result, current_signature)
    elif st.session_state.get("audio_path"):
        st.markdown("### Transcript")
        st.caption("Your transcript will appear here. Choose a model and language, then start transcription.")
    else:
        st.markdown("### Transcript")
        st.caption("Your transcript and export files will appear here after processing.")

    st.markdown(
        '<p class="subtle" style="margin-top:2rem">Powered by faster-whisper · Runs locally · Accuracy varies with recording quality, language and accent.</p>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
