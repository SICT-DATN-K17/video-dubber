from __future__ import annotations

import asyncio
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
	"""Vietnamese text-to-speech wrapper for edge-tts and gTTS."""

	def __init__(self, engine: str = "edge-tts", voice: str = "female", tts_dir: str | Path | None = None):
		self.engine = (engine or "edge-tts").strip().lower()
		self.voice = voice
		self.tts_dir = Path(tts_dir) if tts_dir else TEMP_DIR / "tts"
		self.tts_dir.mkdir(parents=True, exist_ok=True)

		self.edge_voice = "vi-VN-HoaiMyNeural" if voice == "female" else "vi-VN-NamMinhNeural"

	def synthesize_all(self, segments: List[Segment]) -> List[tuple]:
		"""Return list of (segment, path) pairs — only for successfully synthesized segments."""
		results: List[tuple] = []
		error_samples: list[str] = []
		valid_segments = 0
		for idx, segment in enumerate(segments):
			text = (segment.translated or segment.text).strip()
			if not self._is_tts_text_valid(text):
				continue
			valid_segments += 1
			out = self.tts_dir / f"seg_{idx:05d}.mp3"
			try:
				self.synthesize_text(text, out)
				self._adjust_audio_duration(out, max(0, segment.end - segment.start))
				results.append((segment, out))
			except Exception as exc:
				# Fallback to gTTS for non-gTTS engines
				if self.engine != "gtts":
					try:
						self._synthesize_gtts(text, out)
						self._adjust_audio_duration(out, max(0, segment.end - segment.start))
						results.append((segment, out))
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

		if not results:
			detail = (
				f"TTS generated 0 files (engine={self.engine}, "
				f"segments={len(segments)}, valid_segments={valid_segments})."
			)
			if error_samples:
				detail += " Sample errors: " + " | ".join(error_samples)
			raise RuntimeError(detail)
		return results

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

	def synthesize_text(self, text: str, output_path: str | Path) -> Path:
		output_path = Path(output_path)
		output_path.parent.mkdir(parents=True, exist_ok=True)

		if self.engine == "edge-tts":
			self._synthesize_edge(text, output_path)
			return output_path
		if self.engine == "gtts":
			self._synthesize_gtts(text, output_path)
			return output_path
		raise ValueError(f"Unsupported TTS engine: {self.engine}")

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
				# Mỗi lần gọi tạo event loop mới riêng cho thread hiện tại.
				# Tránh dùng asyncio.run() vì có thể conflict với loop của Flask thread.
				loop = asyncio.new_event_loop()
				try:
					loop.run_until_complete(_run())
				finally:
					loop.close()

				if output_path.exists() and output_path.stat().st_size > 0:
					return
				raise RuntimeError("edge-tts returned empty audio output")
			except Exception as exc:
				last_exc = exc
				msg = str(exc)
				if output_path.exists() and output_path.stat().st_size == 0:
					output_path.unlink(missing_ok=True)
				is_retryable = (
					"No audio was received" in msg
					or "empty audio output" in msg
					or "WinError" in msg
					or "ConnectionResetError" in msg
				)
				if not is_retryable or attempt == 2:
					raise RuntimeError(f"edge-tts failed after {attempt + 1} attempt(s): {msg}") from exc
				time.sleep(0.5 * (attempt + 1))

		raise RuntimeError(f"edge-tts failed: {last_exc}")

