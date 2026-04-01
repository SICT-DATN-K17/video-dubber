from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List

from config.settings import TEMP_DIR
from core.transcriber import Segment


class TTSEngine:
	"""Vietnamese text-to-speech wrapper for edge-tts and gTTS."""

	def __init__(self, engine: str = "edge-tts", voice: str = "female"):
		self.engine = engine
		self.voice = voice
		self.tts_dir = TEMP_DIR / "tts"
		self.tts_dir.mkdir(parents=True, exist_ok=True)

		self.edge_voice = "vi-VN-HoaiMyNeural" if voice == "female" else "vi-VN-NamMinhNeural"

	def synthesize_all(self, segments: List[Segment]) -> List[Path]:
		paths: List[Path] = []
		for idx, segment in enumerate(segments):
			text = (segment.translated or segment.text).strip()
			if not text:
				continue
			out = self.tts_dir / f"seg_{idx:05d}.mp3"
			self.synthesize_text(text, out)
			paths.append(out)
		return paths

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

	def _synthesize_edge(self, text: str, output_path: Path) -> None:
		try:
			import edge_tts
		except Exception as exc:
			raise RuntimeError("Missing dependency 'edge-tts'. Install with: pip install edge-tts") from exc

		async def _run() -> None:
			communicate = edge_tts.Communicate(text=text, voice=self.edge_voice)
			await communicate.save(str(output_path))

		asyncio.run(_run())

	@staticmethod
	def _synthesize_gtts(text: str, output_path: Path) -> None:
		try:
			from gtts import gTTS
		except Exception as exc:
			raise RuntimeError("Missing dependency 'gTTS'. Install with: pip install gTTS") from exc

		tts = gTTS(text=text, lang="vi")
		tts.save(str(output_path))

