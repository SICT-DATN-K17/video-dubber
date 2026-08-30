"""
core/translator/openai_translator.py
Dịch EN → VI bằng OpenAI GPT, tối ưu cho thuật ngữ AI/ML.
"""
from __future__ import annotations

from typing import List

from openai import OpenAI

from config.settings import OPENAI_API_KEY, OPENAI_MODEL
from core.translator.base import BaseTranslator
from core.translator.llm_common import (
    SYSTEM_PROMPT,
    build_batch_prompt,
    parse_numbered_lines,
)
from core.transcriber import Segment


class OpenAITranslator(BaseTranslator):
    """Dịch bằng OpenAI GPT-4o."""

    def __init__(self, api_key: str = OPENAI_API_KEY, model: str = OPENAI_MODEL):
        if not api_key:
            raise ValueError("OPENAI_API_KEY chưa được thiết lập!")
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self._cache: dict[str, str] = {}

    @property
    def name(self) -> str:
        return f"OpenAI {self.model}"

    def translate_text(self, text: str) -> str:
        """Dịch một đoạn văn ngắn."""
        if text in self._cache:
            return self._cache[text]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.3,
            max_tokens=500,
        )
        translated = response.choices[0].message.content.strip()
        self._cache[text] = translated
        return translated

    def translate_batch(self, texts: List[str]) -> List[str]:
        """
        Dịch theo batch để tiết kiệm API call.
        Ghép nhiều câu thành 1 request, phân tách bằng dấu hiệu đặc biệt.
        """
        if not texts:
            return []

        segments = [Segment(start=0, end=0, text=t) for t in texts]
        translated_segments = self.translate_segments_batch(segments)
        return [seg.translated for seg in translated_segments]

    def translate_segments_batch(self, segments: List[Segment], batch_size: int = 10) -> List[Segment]:
        for i in range(0, len(segments), batch_size):
            batch = segments[i : i + batch_size]
            texts = [seg.text for seg in batch]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_batch_prompt(texts)},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            raw = response.choices[0].message.content.strip()
            parts = parse_numbered_lines(raw)

            for j, seg in enumerate(batch):
                seg.translated = parts.get(j + 1) or seg.text

        return segments
