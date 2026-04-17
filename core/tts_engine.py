from __future__ import annotations

import asyncio
import importlib
import re
import sys
import time
from pathlib import Path
from typing import List

# Fix Windows CP1252 charmap error: force UTF-8 for stdout/stderr
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from config.settings import TEMP_DIR
from core.transcriber import Segment


class TTSEngine:
	"""Vietnamese text-to-speech wrapper for edge-tts, gTTS, VietTTS, and F5-TTS."""

	def __init__(self, engine: str = "edge-tts", voice: str = "female"):
		self.engine = (engine or "edge-tts").strip().lower()
		self.voice = voice
		self.tts_dir = TEMP_DIR / "tts"
		self.tts_dir.mkdir(parents=True, exist_ok=True)

		self.edge_voice = "vi-VN-HoaiMyNeural" if voice == "female" else "vi-VN-NamMinhNeural"

	def synthesize_all(self, segments: List[Segment], ref_audio_path: Path = None) -> List[Path]:
		paths: List[Path] = []
		error_samples: list[str] = []
		valid_segments = 0
		for idx, segment in enumerate(segments):
			text = (segment.translated or segment.text).strip()
			if not self._is_tts_text_valid(text):
				continue
			valid_segments += 1
			out = self.tts_dir / f"seg_{idx:05d}.mp3"
			try:
				self.synthesize_text(text, out, ref_audio_path=ref_audio_path)
				self._adjust_audio_duration(out, max(0, segment.end - segment.start))
				paths.append(out)
			except Exception as exc:
				# f5-cloud không fallback sang gTTS — hiện lỗi thật để debug
				if self.engine == "f5-cloud":
					print(f"[F5-Cloud] ❌ ERROR segment {idx}: {exc}")
					raise  # Re-raise để lỗi hiện ra trên Streamlit UI
				# Fallback to gTTS for non-gTTS engines to avoid empty output runs.
				if self.engine != "gtts":
					try:
						self._synthesize_gtts(text, out)
						self._adjust_audio_duration(out, max(0, segment.end - segment.start))
						paths.append(out)
						print(f"[TTS] Segment {idx}: fallback gTTS succeeded (primary error: {exc})")
					except Exception as fb_exc:
						err_msg = f"segment {idx}: {exc}; fallback gTTS failed: {fb_exc}"
						print(f"[TTS] Skipping {err_msg}")
						if len(error_samples) < 5:
							error_samples.append(err_msg)
				else:
					err_msg = f"segment {idx}: {exc}"
					print(f"[TTS] Skipping {err_msg}")
					if len(error_samples) < 5:
						error_samples.append(err_msg)

		if not paths:
			detail = (
				f"TTS generated 0 files (engine={self.engine}, "
				f"segments={len(segments)}, valid_segments={valid_segments})."
			)
			if error_samples:
				detail += " Sample errors: " + " | ".join(error_samples)
			raise RuntimeError(detail)
		return paths

	def _adjust_audio_duration(self, audio_path: Path, target_duration: float, max_speed: float = 1.35) -> None:
		"""
		Điều chỉnh độ dài âm thanh để khớp với duration của đoạn video.
		(Áp dụng cách 1 và cách 2: Silence Trimming & Audio Speedup).
		"""
		if target_duration <= 0:
			return
		
		try:
			from pydub import AudioSegment
			from pydub.silence import detect_nonsilent
			from pydub.effects import speedup
			
			audio = AudioSegment.from_file(str(audio_path))
			if len(audio) == 0:
				return
			
			# 1. Option 2: Cắt bớt khoảng trống đầu/cuối của audio (Silence Trimming)
			nonsilent_ranges = detect_nonsilent(audio, min_silence_len=150, silence_thresh=-45)
			if nonsilent_ranges:
				start_trim = nonsilent_ranges[0][0]
				end_trim = nonsilent_ranges[-1][1]
				audio = audio[start_trim:end_trim]

			current_dur = len(audio) / 1000.0
			
			# 2. Option 1: Tăng tốc nếu độ dài audio lớn hơn so với thời gian của segment (Audio Speedup)
			if current_dur > target_duration + 0.1: # Chỉ ép tốc độ nếu audio bị dài hơn quá 0.1s
				rate = current_dur / target_duration
				rate = min(rate, max_speed) # Không được ép tốc độ quá max_speed, kẻo giọng chói
				
				if rate > 1.05:
					# chunk_size=50, crossfade=25 cho result mượt mà
					audio = speedup(audio, playback_speed=rate, chunk_size=50, crossfade=25)

			# Xuất đè lên lại file cũ
			ext = audio_path.suffix.lstrip(".")
			if ext == "": 
				ext = "mp3"
			audio.export(str(audio_path), format=ext)
			
		except Exception as exc:
			print(f"[TTS] Áp dụng Silence Trimming & Speedup thất bại cho {audio_path}: {exc}")

	@staticmethod
	def _is_tts_text_valid(text: str) -> bool:
		"""Filter out noisy/non-speech-like text that frequently breaks neural TTS."""
		normalized = re.sub(r"\s+", " ", text).strip()
		if not normalized:
			return False
		# Keep only text with meaningful alphanumeric content.
		alnum_count = sum(ch.isalnum() for ch in normalized)
		if alnum_count < 2:
			return False
		# Skip pure punctuation/symbol segments.
		if not re.search(r"[\w\d]", normalized, flags=re.UNICODE):
			return False
		return True

	def synthesize_text(self, text: str, output_path: str | Path, ref_audio_path: Path = None, use_demucs: bool = True) -> Path:
		output_path = Path(output_path)
		output_path.parent.mkdir(parents=True, exist_ok=True)

		if self.engine == "edge-tts":
			self._synthesize_edge(text, output_path)
			return output_path
		if self.engine == "gtts":
			self._synthesize_gtts(text, output_path)
			return output_path
		if self.engine in {"f5-tts", "f5_tts", "f5tts"}:
			ref_vocal_path = None
			if ref_audio_path is not None:
				if use_demucs:
					try:
						from core.demucs_utils import separate_vocals
						ref_vocal_path = separate_vocals(ref_audio_path)
					except Exception as exc:
						print(f"[TTS] Demucs error: {exc}. Using original audio as reference.")
						ref_vocal_path = ref_audio_path
				else:
					ref_vocal_path = ref_audio_path
			self._synthesize_f5tts(text, output_path, ref_audio_path=ref_vocal_path)
			return output_path
		if self.engine == "f5-cloud":
			ref_vocal_path = None
			if ref_audio_path is not None:
				if use_demucs:
					try:
						from core.demucs_utils import separate_vocals
						ref_vocal_path = separate_vocals(ref_audio_path)
					except Exception as exc:
						print(f"[TTS] Demucs error: {exc}. Using original audio as reference.")
						ref_vocal_path = ref_audio_path
				else:
					ref_vocal_path = ref_audio_path
			self._synthesize_f5tts_cloud(text, output_path, ref_audio_path=ref_vocal_path)
			return output_path
		raise ValueError(f"Unsupported TTS engine: {self.engine}")

	def _synthesize_f5tts(self, text: str, output_path: Path, ref_audio_path: Path = None, ref_text: str = "") -> None:
		"""
		Adapter F5-TTS (E2TTS backbone) dùng model Vietnamese local.
		Sử dụng đúng Python API của package f5-tts:
		  - load_model / load_vocoder để khởi tạo (cache sau lần đầu)
		  - preprocess_ref_audio_text để chuẩn hoá audio mẫu
		  - infer_process để sinh giọng
		
		ref_audio_path : đường dẫn file wav/mp3 mẫu để clone giọng.
		ref_text       : transcript của đoạn audio mẫu (để trống thì F5-TTS
		                 tự ASR, chậm hơn nhưng vẫn chạy).
		"""
		import yaml
		import torch
		import numpy as np
		import soundfile as sf
		from pathlib import Path as _Path

		# ── Đường dẫn model local ─────────────────────────────────────────
		tts_dir = _Path(__file__).resolve().parent.parent / "F5-TTS-Vietnamese"
		config_path = tts_dir / "config.yaml"
		model_path  = tts_dir / "model_last.pt"
		vocab_path  = tts_dir / "vocab.txt"

		for p in (config_path, model_path, vocab_path):
			if not p.exists():
				raise FileNotFoundError(f"[F5-TTS] Không tìm thấy file: {p}")

		# ── Lazy-load model + vocoder (chỉ load 1 lần) ────────────────────
		if not hasattr(self, "_f5tts_model") or self._f5tts_model is None:
			from f5_tts.model import UNetT
			from f5_tts.infer.utils_infer import load_model, load_vocoder

			with open(config_path, "r", encoding="utf-8") as f:
				cfg = yaml.safe_load(f)

			model_cfg = cfg.get("model", {})
			arch_cfg  = model_cfg.get("arch", {})
			mel_cfg   = model_cfg.get("mel_spec", {})
			mel_spec_type = mel_cfg.get("mel_spec_type", "vocos")

			# Cấu hình arch cho UNetT (E2TTS_Base)
			unet_cfg = dict(
				dim        = arch_cfg.get("dim", 1024),
				depth      = arch_cfg.get("depth", 24),
				heads      = arch_cfg.get("heads", 16),
				ff_mult    = arch_cfg.get("ff_mult", 4),
				pe_attn_head = arch_cfg.get("pe_attn_head", 1),
				text_mask_padding = arch_cfg.get("text_mask_padding", False),
			)

			device = "cuda" if torch.cuda.is_available() else "cpu"
			print(f"[F5-TTS] Loading model from {model_path} on {device}...")

			self._f5tts_model = load_model(
				model_cls    = UNetT,
				model_cfg    = unet_cfg,
				ckpt_path    = str(model_path),
				mel_spec_type= mel_spec_type,
				vocab_file   = str(vocab_path),
				use_ema      = True,
				device       = device,
			)

			self._f5tts_vocoder = load_vocoder(
				vocoder_name = mel_spec_type,
				is_local     = False,
				device       = device,
			)
			self._f5tts_mel_type = mel_spec_type
			self._f5tts_device   = device
			print("[F5-TTS] Model + vocoder ready.")

		# ── Chuẩn bị audio mẫu ───────────────────────────────────────────
		if ref_audio_path is None:
			raise ValueError(
				"[F5-TTS] ref_audio_path is required for voice cloning."
			)
		ref_audio_path = _Path(ref_audio_path)
		if not ref_audio_path.exists():
			raise FileNotFoundError(f"[F5-TTS] Reference audio not found: {ref_audio_path}")

		from f5_tts.infer.utils_infer import preprocess_ref_audio_text, infer_process

		# preprocess_ref_audio_text cần path dạng str
		ref_audio_proc, ref_text_proc = preprocess_ref_audio_text(
			str(ref_audio_path),
			ref_text,  # chuỗi rỗng => F5-TTS tự ASR
		)

		# ── Inference ────────────────────────────────────────────────────
		print(f"[F5-TTS] Generating speech for: {text[:60].encode('ascii', 'replace').decode()}...")
		final_wave, final_sr, _ = infer_process(
			ref_audio   = ref_audio_proc,
			ref_text    = ref_text_proc,
			gen_text    = text,
			model_obj   = self._f5tts_model,
			vocoder     = self._f5tts_vocoder,
			mel_spec_type = self._f5tts_mel_type,
			device      = self._f5tts_device,
		)

		# ── Ghi kết quả ra file ──────────────────────────────────────────
		# output_path có thể là .mp3, nhưng soundfile chỉ ghi .wav trực tiếp
		import tempfile, shutil
		wav_tmp = _Path(output_path).with_suffix(".f5tmp.wav")
		sf.write(str(wav_tmp), final_wave, final_sr)

		# Convert sang định dạng đích (mp3 / wav) bằng pydub nếu cần
		if _Path(output_path).suffix.lower() != ".wav":
			try:
				from pydub import AudioSegment
				AudioSegment.from_wav(str(wav_tmp)).export(str(output_path), format="mp3")
				wav_tmp.unlink(missing_ok=True)
			except Exception as cvt_err:
				# Fallback: copy wav file as output
				print(f"[F5-TTS] Convert to mp3 failed ({cvt_err}), using WAV instead.")
				shutil.copy2(str(wav_tmp), str(output_path))
				wav_tmp.unlink(missing_ok=True)
		else:
			shutil.move(str(wav_tmp), str(output_path))

		if not _Path(output_path).exists() or _Path(output_path).stat().st_size == 0:
			raise RuntimeError("[F5-TTS] No valid audio file was created.")

	def _synthesize_f5tts_cloud(self, text: str, output_path: Path, ref_audio_path: Path = None) -> None:
		"""
		Synthesize speech using F5-TTS Vietnamese đã deploy trên Modal Cloud.
		Dùng modal.Function.lookup() để gọi đúng cách từ process bên ngoài (Streamlit).
		App phải được deploy trước bằng: modal deploy server/f5_cloud.py
		"""
		if ref_audio_path is None:
			raise ValueError("[F5-Cloud] ref_audio_path is required for voice cloning.")
		
		ref_audio_path = Path(ref_audio_path)
		if not ref_audio_path.exists():
			raise FileNotFoundError(f"[F5-Cloud] Reference audio not found: {ref_audio_path}")

		# Dùng from_name() — API chuẩn của Modal phiên bản mới (≥0.73)
		# App name và function name phải khớp với server/f5_cloud.py
		try:
			import modal
			# Modal ≥ 0.73 dùng from_name, các phiên bản cũ hơn dùng lookup
			if hasattr(modal.Function, "from_name"):
				generate_voice_cloud = modal.Function.from_name(
					"f5-tts-vietnamese-service",  # Tên app trong f5_cloud.py
					"generate_voice_cloud"         # Tên function
				)
			else:
				generate_voice_cloud = modal.Function.lookup(
					"f5-tts-vietnamese-service",
					"generate_voice_cloud"
				)
		except Exception as exc:
			raise RuntimeError(
				f"[F5-Cloud] Không kết nối được Modal (app chưa deploy?): {exc}\n"
				"Hãy chạy: modal deploy server/f5_cloud.py"
			) from exc

		print(f"[F5-Cloud] Sending request to Modal for: {text[:50]}...")
		
		with open(ref_audio_path, "rb") as f:
			ref_bytes = f.read()

		try:
			# Gọi function đã deploy trên cloud
			result_bytes = generate_voice_cloud.remote(text=text, ref_audio_bytes=ref_bytes)
			
			# Kiểm tra xem Cloud có trả về thông báo lỗi thay vì audio không
			if isinstance(result_bytes, bytes) and result_bytes.startswith(b"ERROR"):
				err_msg = result_bytes.decode()
				print(f"[F5-Cloud] Modal Error: {err_msg}")
				raise RuntimeError(err_msg)

			# Save result
			with open(output_path, "wb") as f:
				f.write(result_bytes)
				
			if not output_path.exists() or output_path.stat().st_size == 0:
				raise RuntimeError("[F5-Cloud] Cloud returned empty result.")
			
			print(f"[F5-Cloud] Success: Generated audio for segment.")
				
		except Exception as exc:
			raise RuntimeError(f"[F5-Cloud] Error during cloud synthesis: {exc}") from exc

	def _synthesize_gtts(self, text: str, output_path: Path) -> None:
		"""Synthesize speech using Google TTS (gTTS)."""
		try:
			from gtts import gTTS
		except ImportError as exc:
			raise RuntimeError("Missing package gTTS. Install with: pip install gTTS") from exc
		tts_obj = gTTS(text=text, lang="vi", slow=False)
		tts_obj.save(str(output_path))
		if not output_path.exists() or output_path.stat().st_size == 0:
			raise RuntimeError("gTTS produced no valid audio file.")

	# Fix asyncio in _synthesize_edge:
	def _synthesize_edge(self, text: str, output_path: Path) -> None:
		try:
			import edge_tts
		except Exception as exc:
			raise RuntimeError("Missing dependency 'edge-tts'. Install with: pip install edge-tts") from exc

		async def _run() -> None:
			communicate = edge_tts.Communicate(text=text, voice=self.edge_voice)
			await communicate.save(str(output_path))

		last_exc: Exception | None = None
		for attempt in range(3):
			try:
				# Xử lý trường hợp đã có event loop (Streamlit, Jupyter)
				try:
					loop = asyncio.get_running_loop()
				except RuntimeError:
					loop = None

				if loop and loop.is_running():
					import nest_asyncio
					nest_asyncio.apply()
					loop.run_until_complete(_run())
				else:
					asyncio.run(_run())

				if output_path.exists() and output_path.stat().st_size > 0:
					return
				raise RuntimeError("edge-tts returned empty audio output")
			except Exception as exc:
				last_exc = exc
				msg = str(exc)
				if output_path.exists() and output_path.stat().st_size == 0:
					output_path.unlink(missing_ok=True)
				is_retryable = "No audio was received" in msg or "empty audio output" in msg
				if not is_retryable or attempt == 2:
					raise RuntimeError(f"edge-tts failed after {attempt + 1} attempt(s): {msg}") from exc
				time.sleep(0.35 * (attempt + 1))

		raise RuntimeError(f"edge-tts failed: {last_exc}")

