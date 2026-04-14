from __future__ import annotations

import asyncio
import importlib
import re
import time
from pathlib import Path
from typing import List

from config.settings import TEMP_DIR
from core.transcriber import Segment


class TTSEngine:
	"""Vietnamese text-to-speech wrapper for edge-tts, gTTS and VietTTS."""

	def __init__(self, engine: str = "edge-tts", voice: str = "female"):
		self.engine = (engine or "edge-tts").strip().lower()
		self.voice = voice
		self.tts_dir = TEMP_DIR / "tts"
		self.tts_dir.mkdir(parents=True, exist_ok=True)

		self.edge_voice = "vi-VN-HoaiMyNeural" if voice == "female" else "vi-VN-NamMinhNeural"
		self.valtec_speaker = "NF" if voice == "female" else "NM1"

	def synthesize_all(self, segments: List[Segment]) -> List[Path]:
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
				self.synthesize_text(text, out)
				paths.append(out)
			except Exception as exc:
				# Fallback to gTTS for non-gTTS engines to avoid empty output runs.
				if self.engine != "gtts":
					try:
						self._synthesize_gtts(text, out)
						paths.append(out)
						print(f"[TTS] Segment {idx}: fallback gTTS succeeded (primary error: {exc})")
						continue
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
		if self.engine in {"viettts", "viet-tts", "viet_tts"}:
			self._synthesize_viettts(text, output_path)
			return output_path

		raise ValueError(f"Unsupported TTS engine: {self.engine}")

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
				asyncio.run(_run())
				if output_path.exists() and output_path.stat().st_size > 0:
					return
				raise RuntimeError("edge-tts returned empty audio output")
			except Exception as exc:
				last_exc = exc
				msg = str(exc)
				if output_path.exists() and output_path.stat().st_size == 0:
					output_path.unlink(missing_ok=True)

				# Retry transient edge-tts failures; otherwise fail fast.
				is_retryable = "No audio was received" in msg or "empty audio output" in msg
				if not is_retryable or attempt == 2:
					raise RuntimeError(f"edge-tts failed after {attempt + 1} attempt(s): {msg}") from exc
				time.sleep(0.35 * (attempt + 1))

		raise RuntimeError(f"edge-tts failed: {last_exc}")

	@staticmethod
	def _synthesize_gtts(text: str, output_path: Path) -> None:
		try:
			from gtts import gTTS
		except Exception as exc:
			raise RuntimeError("Missing dependency 'gTTS'. Install with: pip install gTTS") from exc

		tts = gTTS(text=text, lang="vi")
		tts.save(str(output_path))

	def _synthesize_viettts(self, text: str, output_path: Path) -> None:
		"""
		Best-effort adapter for VietTTS package variants.
		Supports a few common APIs and validates output file existence.
		"""
		# Preferred implementation requested by user: from valtec_tts import TTS
		try:
			from valtec_tts import TTS as ValtecTTS
		except Exception:
			ValtecTTS = None

		if ValtecTTS is not None:
			errors: list[str] = []
			try:
				engine = ValtecTTS()
			except Exception as exc:
				errors.append(f"init failed: {exc}")
			else:
				try:
					result = engine.speak(
						text=text,
						output_path=str(output_path),
						speaker=self.valtec_speaker,
					)
					if asyncio.iscoroutine(result):
						asyncio.run(result)
					if output_path.exists() and output_path.stat().st_size > 0:
						return
				except Exception as exc:
					errors.append(f"speak failed: {exc}")

				# Fallback: synthesize() returns (audio, sample_rate)
				try:
					import soundfile as sf
					audio, sample_rate = engine.synthesize(text=text, speaker=self.valtec_speaker)
					sf.write(str(output_path), audio, sample_rate)
					if output_path.exists() and output_path.stat().st_size > 0:
						return
				except Exception as exc:
					errors.append(f"synthesize failed: {exc}")

			raise RuntimeError("ValtecTTS available but synthesis failed: " + " | ".join(errors))

		module = None
		import_errors: list[str] = []
		for name in ("vietTTS", "viettts", "viet_tts"):
			try:
				module = importlib.import_module(name)
				break
			except Exception as exc:
				import_errors.append(f"{name}: {exc}")

		if module is None:
			raise RuntimeError(
				"Missing dependency 'VietTTS'. Install package and ensure module is importable "
				"(tried: vietTTS, viettts, viet_tts)."
			)

		def _handle_result(result: object) -> bool:
			if output_path.exists() and output_path.stat().st_size > 0:
				return True
			if isinstance(result, (bytes, bytearray)):
				output_path.write_bytes(bytes(result))
				return output_path.exists() and output_path.stat().st_size > 0
			if isinstance(result, str):
				candidate = Path(result)
				if candidate.exists() and candidate.stat().st_size > 0:
					output_path.write_bytes(candidate.read_bytes())
					return True
			return output_path.exists() and output_path.stat().st_size > 0

		def _call(func, *args, **kwargs) -> bool:
			if not callable(func):
				return False
			result = func(*args, **kwargs)
			if asyncio.iscoroutine(result):
				result = asyncio.run(result)
			return _handle_result(result)

		attempts = [
			lambda: _call(getattr(module, "text_to_speech", None), text, str(output_path)),
			lambda: _call(getattr(module, "synthesize", None), text, str(output_path)),
			lambda: _call(getattr(module, "tts", None), text, str(output_path)),
			lambda: _call(getattr(module, "text_to_speech", None), text=text, output_path=str(output_path)),
			lambda: _call(getattr(module, "synthesize", None), text=text, output_path=str(output_path)),
			lambda: _call(getattr(module, "tts", None), text=text, output_path=str(output_path)),
		]

		for class_name in ("VietTTS", "TTS", "Synthesizer"):
			cls = getattr(module, class_name, None)
			if cls is None:
				continue
			try:
				obj = cls()
			except Exception:
				continue
			attempts.extend(
				[
					lambda obj=obj: _call(getattr(obj, "text_to_speech", None), text, str(output_path)),
					lambda obj=obj: _call(getattr(obj, "synthesize", None), text, str(output_path)),
					lambda obj=obj: _call(getattr(obj, "tts", None), text, str(output_path)),
					lambda obj=obj: _call(getattr(obj, "text_to_speech", None), text=text, output_path=str(output_path)),
					lambda obj=obj: _call(getattr(obj, "synthesize", None), text=text, output_path=str(output_path)),
					lambda obj=obj: _call(getattr(obj, "tts", None), text=text, output_path=str(output_path)),
				]
			)

		for try_call in attempts:
			try:
				if try_call():
					return
			except TypeError:
				continue
			except Exception:
				continue

		raise RuntimeError(
			"VietTTS module loaded but no compatible synthesis API produced audio. "
			"Expected an API like text_to_speech/synthesize/tts that accepts text and output path."
		)

