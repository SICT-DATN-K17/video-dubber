"""
app.py — Streamlit Demo: AI Video Dubbing (EN → VI)
Chạy: streamlit run app.py
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

# Work around Streamlit watcher + transformers lazy import issues.
os.environ.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none")

import streamlit as st

# ── Cấu hình trang ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Video Dubbing",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS tùy chỉnh ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: #0f0f13; }
    [data-testid="stSidebar"] { background: #16161d; border-right: 1px solid #2a2a3a; }
    h1 { color: #e0e0ff; font-size: 2rem !important; }
    h2, h3 { color: #b0b0d0; }
    .step-card {
        background: #1a1a26;
        border: 1px solid #2a2a40;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
    }
    .success-badge {
        background: #1a3a2a;
        color: #4eff9f;
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .engine-badge {
        background: #1a2a3a;
        color: #4eb8ff;
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 0.8rem;
    }
    .stProgress > div > div { background: linear-gradient(90deg, #4e54ff, #4eb8ff); }
</style>
""", unsafe_allow_html=True)


# ── Header ───────────────────────────────────────────────────────────────────
col_title, col_badge = st.columns([4, 1])
with col_title:
    st.markdown("## 🎙️ AI Video Dubbing — Lồng tiếng AI/ML")
    st.caption("Tự động dịch & lồng tiếng video tiếng Anh sang tiếng Việt · Chuyên lĩnh vực AI")


# ── Sidebar: Cài đặt ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Cài đặt")

    # Engine dịch
    st.markdown("**Engine dịch**")
    translator_choice = st.radio(
        "Chọn engine",
        options=["OpenAI GPT-4o", "MarianMT (Offline)"],
        index=0,
        label_visibility="collapsed",
        help="OpenAI cho chất lượng cao hơn; MarianMT chạy offline không cần API key.",
    )

    if "OpenAI" in translator_choice:
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            placeholder="sk-...",
            value=os.getenv("OPENAI_API_KEY", ""),
        )
        openai_model = st.selectbox(
            "Model",
            ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
        )

    st.divider()

    # Cài đặt Whisper
    st.markdown("**Whisper STT**")
    whisper_model = st.select_slider(
        "Model size",
        options=["tiny", "base", "small", "medium", "large"],
        value="base",
        help="Larger = chính xác hơn nhưng chậm hơn",
    )

    st.divider()

    # Cài đặt TTS
    st.markdown("**Text-to-Speech**")
    tts_engine = st.radio(
        "TTS engine",
        ["edge-tts (Microsoft Neural)", "gTTS (Google)"],
        label_visibility="collapsed",
    )
    tts_voice = st.radio(
        "Giọng",
        ["Nữ (HoaiMy)", "Nam (NamMinh)"],
        label_visibility="collapsed",
        horizontal=True,
    )

    st.divider()

    # Cài đặt ghép video
    st.markdown("**Âm thanh đầu ra**")
    original_vol = st.slider(
        "Volume gốc (%)",
        min_value=0, max_value=50, value=10, step=5,
        help="0% = tắt hoàn toàn âm thanh gốc",
    )
    subtitle_mode = st.selectbox(
        "Phụ đề",
        ["Song ngữ (EN + VI)", "Chỉ tiếng Việt", "Chỉ tiếng Anh", "Không có"],
        index=0,
    )


# ── Main area ────────────────────────────────────────────────────────────────
tab_upload, tab_result, tab_about = st.tabs(["📤 Xử lý video", "📥 Kết quả", "ℹ️ Hướng dẫn"])

# ─── Tab 1: Upload & Process ─────────────────────────────────────────────────
with tab_upload:
    uploaded_file = st.file_uploader(
        "Tải lên video tiếng Anh (MP4, MOV, AVI, MKV)",
        type=["mp4", "mov", "avi", "mkv"],
        help="Video về AI/ML sẽ cho kết quả dịch thuật tốt nhất.",
    )

    if uploaded_file:
        st.video(uploaded_file)

        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("Tên file", uploaded_file.name)
        with col_info2:
            size_mb = uploaded_file.size / (1024 * 1024)
            st.metric("Kích thước", f"{size_mb:.1f} MB")
        with col_info3:
            engine_label = "OpenAI GPT-4o" if "OpenAI" in translator_choice else "MarianMT"
            st.metric("Engine dịch", engine_label)

        st.divider()

        if st.button("🚀 Bắt đầu lồng tiếng", type="primary", width="stretch"):
            # Kiểm tra API key nếu dùng OpenAI
            if "OpenAI" in translator_choice and not api_key:
                st.error("⚠️ Vui lòng nhập OpenAI API Key!")
                st.stop()

            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                from config.settings import TEMP_DIR, OUTPUT_DIR
                from core.audio_extractor import AudioExtractor
                from core.transcriber import Transcriber
                from core.translator import get_translator
                from core.tts_engine import TTSEngine
                from core.video_composer import VideoComposer
                from utils.subtitle_utils import segments_to_srt

                # Lưu file upload tạm
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=Path(uploaded_file.name).suffix,
                    dir=str(TEMP_DIR),
                ) as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_video_path = Path(tmp.name)

                # ── Bước 1: Tách audio ─────────────────────────────────
                status_text.markdown("**⏳ Bước 1/5:** Đang tách audio từ video...")
                progress_bar.progress(10)
                extractor = AudioExtractor()
                audio_path = extractor.extract(tmp_video_path)
                status_text.markdown("✅ **Bước 1/5:** Tách audio thành công!")
                progress_bar.progress(20)

                # ── Bước 2: Transcribe ────────────────────────────────
                status_text.markdown("**⏳ Bước 2/5:** Đang nhận dạng giọng nói (Whisper)...")
                transcriber = Transcriber(model_size=whisper_model)
                segments = transcriber.transcribe(audio_path)
                status_text.markdown(f"✅ **Bước 2/5:** Tìm thấy **{len(segments)}** segment.")
                progress_bar.progress(40)

                # Hiển thị preview transcript
                with st.expander(f"📝 Transcript tiếng Anh ({len(segments)} segment)", expanded=False):
                    for seg in segments[:10]:
                        st.text(f"[{seg.start:.1f}s → {seg.end:.1f}s] {seg.text}")
                    if len(segments) > 10:
                        st.caption(f"... và {len(segments) - 10} segment khác")

                # ── Bước 3: Dịch ──────────────────────────────────────
                status_text.markdown("**⏳ Bước 3/5:** Đang dịch sang tiếng Việt...")
                engine_key = "openai" if "OpenAI" in translator_choice else "marian"
                kwargs = {}
                if engine_key == "openai":
                    kwargs = {"api_key": api_key, "model": openai_model}
                translator = get_translator(engine_key, **kwargs)
                segments = translator.translate_segments(segments)
                status_text.markdown("✅ **Bước 3/5:** Dịch hoàn tất!")
                progress_bar.progress(60)

                # Hiển thị preview dịch
                with st.expander("🌏 Preview bản dịch (so sánh)", expanded=True):
                    for seg in segments[:8]:
                        col_en, col_vi = st.columns(2)
                        with col_en:
                            st.caption("🇬🇧 English")
                            st.text(seg.text)
                        with col_vi:
                            st.caption("🇻🇳 Tiếng Việt")
                            st.text(seg.translated)
                        st.divider()

                # ── Bước 4: TTS ───────────────────────────────────────
                status_text.markdown("**⏳ Bước 4/5:** Đang tổng hợp giọng nói tiếng Việt...")
                engine_str = "edge-tts" if "edge" in tts_engine else "gtts"
                voice_str = "female" if "Nữ" in tts_voice else "male"
                tts = TTSEngine(engine=engine_str, voice=voice_str)
                tts_paths = tts.synthesize_all(segments)
                status_text.markdown("✅ **Bước 4/5:** Tổng hợp giọng nói xong!")
                progress_bar.progress(80)

                # ── Bước 5: Ghép video ────────────────────────────────
                status_text.markdown("**⏳ Bước 5/5:** Đang ghép video lồng tiếng...")
                composer = VideoComposer()
                output_video = composer.compose(
                    video_path=tmp_video_path,
                    segments=segments,
                    tts_paths=tts_paths,
                    original_volume=original_vol / 100.0,
                )

                # Tạo phụ đề
                subtitle_map = {
                    "Song ngữ (EN + VI)": "bilingual",
                    "Chỉ tiếng Việt": "vi",
                    "Chỉ tiếng Anh": "en",
                }
                srt_path = None
                if subtitle_mode != "Không có":
                    srt_content = segments_to_srt(
                        segments,
                        mode=subtitle_map.get(subtitle_mode, "bilingual"),
                        output_path=output_video.with_suffix(".srt"),
                    )
                    srt_path = output_video.with_suffix(".srt")

                progress_bar.progress(100)
                status_text.markdown("🎉 **Hoàn tất! Video lồng tiếng đã sẵn sàng.**")

                # Lưu kết quả vào session state để hiển thị ở tab 2
                st.session_state["output_video"] = output_video
                st.session_state["srt_path"] = srt_path
                st.session_state["segments"] = segments
                st.session_state["processing_done"] = True

                st.success("✅ Lồng tiếng thành công! Chuyển sang tab **Kết quả** để tải xuống.")
                st.balloons()

            except Exception as e:
                st.error(f"❌ Lỗi: {e}")
                st.exception(e)


# ─── Tab 2: Kết quả ──────────────────────────────────────────────────────────
with tab_result:
    if not st.session_state.get("processing_done"):
        st.info("⬅️ Vui lòng upload video và chạy lồng tiếng ở tab **Xử lý video** trước.")
    else:
        output_video: Path = st.session_state["output_video"]
        srt_path: Path | None = st.session_state.get("srt_path")
        segments = st.session_state.get("segments", [])

        st.markdown("### 🎬 Video lồng tiếng")
        if output_video.exists():
            st.video(str(output_video))

            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                with open(output_video, "rb") as f:
                    st.download_button(
                        "⬇️ Tải video lồng tiếng",
                        data=f,
                        file_name=output_video.name,
                        mime="video/mp4",
                        width="stretch",
                    )
            with col_dl2:
                if srt_path and srt_path.exists():
                    with open(srt_path, "rb") as f:
                        st.download_button(
                            "⬇️ Tải phụ đề (.srt)",
                            data=f,
                            file_name=srt_path.name,
                            mime="text/plain",
                            width="stretch",
                        )

        st.divider()
        st.markdown("### 📋 Bản dịch đầy đủ")
        if segments:
            import pandas as pd
            df = pd.DataFrame([
                {
                    "Thời gian": f"{seg.start:.1f}s → {seg.end:.1f}s",
                    "Tiếng Anh": seg.text,
                    "Tiếng Việt": seg.translated,
                }
                for seg in segments
            ])
            st.dataframe(df, width="stretch", height=400)


# ─── Tab 3: Hướng dẫn ────────────────────────────────────────────────────────
with tab_about:
    st.markdown("""
    ## 🏗️ Kiến trúc hệ thống

    ```
    Video (EN) 
      │
      ▼ FFmpeg
    Audio WAV (16kHz mono)
      │
      ▼ OpenAI Whisper
    Transcript EN (segments + timestamps)
      │
      ├─── OpenAI GPT-4o ───┐
      │                     ▼
      └─── MarianMT ──── Bản dịch VI (segments)
                            │
                            ▼ edge-tts / gTTS
                         Audio VI (từng segment)
                            │
                            ▼ ffmpeg overlay
                         Video lồng tiếng (MP4) + Phụ đề (SRT)
    ```

    ## 🔧 So sánh 2 engine dịch

    | Tiêu chí | OpenAI GPT-4o | MarianMT |
    |---|---|---|
    | Chất lượng dịch | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
    | Tốc độ | Nhanh (API) | Phụ thuộc GPU |
    | Chi phí | API Key (có phí) | Miễn phí |
    | Offline | ❌ | ✅ |
    | Thuật ngữ AI | Xuất sắc | Trung bình |

    ## 📦 Cài đặt

    ```bash
    # Clone & setup
    pip install -r requirements.txt

    # Cài ffmpeg (bắt buộc)
    # Ubuntu: sudo apt install ffmpeg
    # Mac: brew install ffmpeg
    # Windows: https://ffmpeg.org/download.html

    # Copy và điền API key
    cp .env.example .env

    # Chạy
    streamlit run app.py
    ```

    ## 💡 Mẹo để có kết quả tốt nhất

    - Dùng video chất lượng âm thanh tốt, ít tiếng ồn nền
    - Chọn Whisper `small` hoặc `medium` cho video dài
    - Dùng OpenAI GPT-4o cho video chuyên sâu về AI/ML
    - MarianMT phù hợp khi cần xử lý offline hoặc tiết kiệm chi phí
    """)