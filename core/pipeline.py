"""
core/pipeline.py
Orchestrator: điều phối toàn bộ pipeline lồng tiếng từ đầu đến cuối.
Dùng được cả từ CLI lẫn Streamlit app.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from config.settings import TEMP_DIR, OUTPUT_DIR
from core.audio_extractor import AudioExtractor
from core.transcriber import Transcriber, Segment
from core.translator import get_translator
from core.tts_engine import TTSEngine
from core.video_composer import VideoComposer
from utils.subtitle_utils import segments_to_srt
from utils.file_utils import clean_temp_dir


@dataclass
class DubbingConfig:
    """Toàn bộ cấu hình cho một lần chạy pipeline."""
    translator_engine: str = "openai"       # "openai" | "marian"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    whisper_model: str = "base"
    compute_device: str = "auto"           # "auto" | "cuda" | "cpu"
    tts_engine: str = "edge-tts"            # "edge-tts" | "gtts"
    tts_voice: str = "female"               # "female" | "male"
    original_volume: float = 0.1            # 0.0 – 1.0
    subtitle_mode: str = "bilingual"        # "bilingual" | "vi" | "en" | "none"
    output_dir: Path = field(default_factory=lambda: OUTPUT_DIR)


@dataclass
class DubbingResult:
    """Kết quả trả về sau khi pipeline hoàn thành."""
    output_video: Optional[Path] = None
    srt_path: Optional[Path] = None
    segments: List[Segment] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    success: bool = False
    error: str = ""


ProgressCallback = Callable[[int, str], None]  # (percent, message)


class DubbingPipeline:
    """
    Pipeline lồng tiếng end-to-end.

    Ví dụ sử dụng:
        config = DubbingConfig(translator_engine="openai", openai_api_key="sk-...")
        pipeline = DubbingPipeline(config)
        result = pipeline.run("my_video.mp4")
        print(result.output_video)
    """

    def __init__(self, config: DubbingConfig):
        self.config = config

    def run(
        self,
        video_path: str | Path,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> DubbingResult:
        """
        Chạy toàn bộ pipeline.

        Args:
            video_path:   Đường dẫn video đầu vào.
            progress_cb:  Hàm callback (percent, message) để cập nhật tiến trình.

        Returns:
            DubbingResult với thông tin kết quả.
        """
        result = DubbingResult()
        t0 = time.time()

        def _progress(pct: int, msg: str):
            if progress_cb:
                progress_cb(pct, msg)
            else:
                print(f"[{pct:3d}%] {msg}")

        try:
            video_path = Path(video_path)
            cfg = self.config

            # ── Bước 1: Tách audio ─────────────────────────────────────
            _progress(10, "Tách audio từ video...")
            extractor = AudioExtractor()
            audio_path = extractor.extract(video_path)
            video_duration = extractor.get_duration(video_path)

            # ── Bước 2: Transcribe ─────────────────────────────────────
            _progress(25, f"Nhận dạng giọng nói (Whisper {cfg.whisper_model})...")
            transcriber = Transcriber(model_size=cfg.whisper_model, device=cfg.compute_device)
            segments = transcriber.transcribe(audio_path)
            _progress(40, f"Tìm thấy {len(segments)} segment.")

            # ── Bước 3: Dịch ───────────────────────────────────────────
            _progress(45, f"Đang dịch với engine: {cfg.translator_engine}...")
            kwargs = {}
            if cfg.translator_engine == "openai":
                kwargs = {"api_key": cfg.openai_api_key, "model": cfg.openai_model}
            elif cfg.translator_engine == "marian":
                kwargs = {"device": cfg.compute_device}
            translator = get_translator(cfg.translator_engine, **kwargs)
            segments = translator.translate_segments(segments)
            _progress(65, "Dịch hoàn tất.")

            # ── Bước 4: TTS ────────────────────────────────────────────
            _progress(70, "Tổng hợp giọng nói tiếng Việt...")
            tts = TTSEngine(engine=cfg.tts_engine, voice=cfg.tts_voice)
            tts_paths = tts.synthesize_all(segments)
            _progress(85, "Tổng hợp giọng xong.")

            # ── Bước 5: Ghép video ─────────────────────────────────────
            _progress(88, "Ghép audio vào video...")
            composer = VideoComposer()
            output_video = composer.compose(
                video_path=video_path,
                segments=segments,
                tts_paths=tts_paths,
                original_volume=cfg.original_volume,
                video_duration=video_duration,
            )

            # ── Bước 6: Tạo phụ đề ────────────────────────────────────
            srt_path = None
            if cfg.subtitle_mode != "none":
                _progress(95, "Tạo file phụ đề...")
                srt_path = output_video.with_suffix(".srt")
                segments_to_srt(segments, mode=cfg.subtitle_mode, output_path=srt_path)

            # ── Hoàn thành ─────────────────────────────────────────────
            _progress(100, "✅ Hoàn tất!")
            result.output_video = output_video
            result.srt_path = srt_path
            result.segments = segments
            result.success = True

        except Exception as e:
            result.error = str(e)
            result.success = False
            _progress(0, f"❌ Lỗi: {e}")

        finally:
            result.elapsed_seconds = time.time() - t0
            # Dọn file tạm
            clean_temp_dir(TEMP_DIR)

        return result