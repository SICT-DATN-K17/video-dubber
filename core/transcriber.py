from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Segment:
	start: float
	end: float
	text: str
	translated: str = ""


class Transcriber:
	"""Speech-to-text using OpenAI Whisper local model."""

	def __init__(self, model_size: str = "base", device: str = "auto"):
		try:
			import whisper
		except Exception as exc:
			raise RuntimeError(
				"Missing dependency 'openai-whisper'. Install with: pip install openai-whisper"
			) from exc

		try:
			import torch
		except Exception as exc:
			raise RuntimeError(
				"Missing dependency 'torch'. Install with: pip install torch"
			) from exc

		requested_device = (device or "auto").strip().lower()
		if requested_device not in {"auto", "cuda", "cpu"}:
			raise ValueError(f"Unsupported device: {device}. Use one of: auto, cuda, cpu")

		if requested_device == "auto":
			resolved_device = "cuda" if torch.cuda.is_available() else "cpu"
		elif requested_device == "cuda":
			if not torch.cuda.is_available():
				print("[Whisper] CUDA requested but unavailable. Falling back to CPU.")
				resolved_device = "cpu"
			else:
				resolved_device = "cuda"
		else:
			resolved_device = "cpu"

		self._whisper = whisper
		self.model_size = model_size
		self.device = resolved_device
		self.use_fp16 = self.device == "cuda"
		try:
			self.model = whisper.load_model(model_size, device=self.device)
		except RuntimeError as exc:
			msg = str(exc).lower()
			if self.device == "cuda" and (
				"out of memory" in msg or "unable to find an engine" in msg
			):
				print("[Whisper] CUDA failed while loading model. Falling back to CPU.")
				self.device = "cpu"
				self.use_fp16 = False
				if torch.cuda.is_available():
					torch.cuda.empty_cache()
				self.model = whisper.load_model(model_size, device=self.device)
			else:
				raise

	def transcribe(self, audio_path: str | Path, language: str = "en") -> List[Segment]:
		audio_path = Path(audio_path)
		if not audio_path.exists():
			raise FileNotFoundError(f"Audio not found: {audio_path}")

		try:
			result = self.model.transcribe(
				str(audio_path),
				language=language,
				fp16=self.use_fp16,
			)
		except RuntimeError as exc:
			msg = str(exc).lower()
			if self.device == "cuda" and (
				"out of memory" in msg or "unable to find an engine" in msg
			):
				print("[Whisper] CUDA failed while transcribing. Retrying on CPU.")
				try:
					import torch
					if torch.cuda.is_available():
						torch.cuda.empty_cache()
				except Exception:
					pass
				self.device = "cpu"
				self.use_fp16 = False
				self.model = self._whisper.load_model(self.model_size, device=self.device)
				result = self.model.transcribe(
					str(audio_path),
					language=language,
					fp16=self.use_fp16,
				)
			else:
				raise
		segments: List[Segment] = []
		for seg in result.get("segments", []):
			text = (seg.get("text") or "").strip()
			if not text:
				continue
			segments.append(
				Segment(
					start=float(seg.get("start", 0.0)),
					end=float(seg.get("end", 0.0)),
					text=text,
				)
			)
		return segments

