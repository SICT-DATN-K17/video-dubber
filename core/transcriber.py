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

	def __init__(self, model_size: str = "base"):
		try:
			import whisper
		except Exception as exc:
			raise RuntimeError(
				"Missing dependency 'openai-whisper'. Install with: pip install openai-whisper"
			) from exc

		self._whisper = whisper
		self.model_size = model_size
		self.model = whisper.load_model(model_size)

	def transcribe(self, audio_path: str | Path, language: str = "en") -> List[Segment]:
		audio_path = Path(audio_path)
		if not audio_path.exists():
			raise FileNotFoundError(f"Audio not found: {audio_path}")

		result = self.model.transcribe(str(audio_path), language=language)
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

