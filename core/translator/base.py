from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from core.transcriber import Segment


class BaseTranslator(ABC):
	@property
	@abstractmethod
	def name(self) -> str:
		raise NotImplementedError

	@abstractmethod
	def translate_text(self, text: str) -> str:
		raise NotImplementedError

	def translate_batch(self, texts: List[str]) -> List[str]:
		return [self.translate_text(t) for t in texts]

	def translate_segments(self, segments: List[Segment]) -> List[Segment]:
		texts = [seg.text for seg in segments]
		translated = self.translate_batch(texts)
		for seg, vi_text in zip(segments, translated):
			seg.translated = vi_text
		return segments

