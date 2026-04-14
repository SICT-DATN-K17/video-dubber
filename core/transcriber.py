from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List


@dataclass
class Segment:
	start: float
	end: float
	text: str
	translated: str = ""


class Transcriber:
	"""Speech-to-text using OpenAI Whisper local model."""

	_SENTENCE_END_RE = re.compile(r"[.!?][\"'\)\]]*$")
	_LEADING_PUNCT_RE = re.compile(r"^[,.;:!?%\)\]\}]+")

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

	@classmethod
	def _join_text_fragments(cls, texts: List[str]) -> str:
		joined = ""
		for part in texts:
			part = (part or "").strip()
			if not part:
				continue
			if not joined:
				joined = part
				continue
			# Avoid adding a space before punctuation-starting fragments.
			if cls._LEADING_PUNCT_RE.match(part):
				joined += part
			else:
				joined += " " + part
		return joined.strip()

	@classmethod
	def _merge_segments_into_sentences(
		cls,
		segments: List[Segment],
		silence_threshold: float = 0.45,
	) -> List[Segment]:
		if not segments:
			return []

		ordered = sorted(segments, key=lambda s: (s.start, s.end))
		merged: List[Segment] = []
		bucket: List[Segment] = []
		bucket_texts: List[str] = []

		for idx, seg in enumerate(ordered):
			if seg.end <= seg.start:
				continue

			text = (seg.text or "").strip()
			if not text:
				continue

			bucket.append(seg)
			bucket_texts.append(text)

			current_text = cls._join_text_fragments(bucket_texts)
			duration = bucket[-1].end - bucket[0].start
			is_last = idx == len(ordered) - 1
			next_gap = 0.0
			next_starts_lower = False
			if not is_last:
				nxt = ordered[idx + 1]
				next_gap = max(0.0, nxt.start - seg.end)
				next_text = (nxt.text or "").lstrip()
				next_starts_lower = bool(next_text) and next_text[0].islower()

			should_flush = False
			if is_last:
				should_flush = True
			elif cls._SENTENCE_END_RE.search(current_text):
				should_flush = True
			elif next_gap >= silence_threshold and not next_starts_lower:
				should_flush = True

			if should_flush and bucket:
				merged.append(
					Segment(
						start=bucket[0].start,
						end=bucket[-1].end,
						text=current_text,
					)
				)
				bucket = []
				bucket_texts = []

		return merged

	def transcribe(
		self,
		audio_path: str | Path,
		language: str = "en",
		sentence_resegment: bool = True,
		silence_threshold: float = 0.45,
	) -> List[Segment]:
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

		if not sentence_resegment:
			return segments

		return self._merge_segments_into_sentences(
			segments,
			silence_threshold=silence_threshold,
		)

