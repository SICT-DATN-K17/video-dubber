"""
core/translator/gemini_translator.py
Dịch EN → VI bằng Google Gemini API, tối ưu cho thuật ngữ AI/ML.
"""
from __future__ import annotations

from typing import List

from google import genai
from google.genai import types

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from core.translator.base import BaseTranslator
from core.translator.llm_common import (
    SYSTEM_PROMPT,
    build_batch_prompt,
    parse_numbered_lines,
)
from core.transcriber import Segment


class GeminiTranslator(BaseTranslator):
    """Dịch bằng Google Gemini (google-genai SDK)."""

    def __init__(self, api_key: str = GEMINI_API_KEY, model: str = GEMINI_MODEL):
        if not api_key:
            raise ValueError("GEMINI_API_KEY chưa được thiết lập!")
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self._cache: dict[str, str] = {}

    @property
    def name(self) -> str:
        return f"Gemini {self.model}"

    def _generate(self, prompt: str, max_output_tokens: int) -> str:
        """Gọi Gemini một lần, tắt 'thinking' nếu model hỗ trợ để giảm độ trễ."""
        base_kwargs = dict(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
            max_output_tokens=max_output_tokens,
        )
        try:
            config = types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                **base_kwargs,
            )
            response = self.client.models.generate_content(
                model=self.model, contents=prompt, config=config
            )
        except Exception:
            # Model không hỗ trợ thinking_config -> gọi lại với cấu hình cơ bản.
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(**base_kwargs),
            )
        return (response.text or "").strip()

    def translate_text(self, text: str) -> str:
        """Dịch một đoạn văn ngắn."""
        if text in self._cache:
            return self._cache[text]

        translated = self._generate(text, max_output_tokens=1000) or text
        self._cache[text] = translated
        return translated

    def translate_batch(self, texts: List[str]) -> List[str]:
        """Dịch theo batch để tiết kiệm API call."""
        if not texts:
            return []

        segments = [Segment(start=0, end=0, text=t) for t in texts]
        translated_segments = self.translate_segments_batch(segments)
        return [seg.translated for seg in translated_segments]

    def translate_segments_batch(self, segments: List[Segment], batch_size: int = 10) -> List[Segment]:
        for i in range(0, len(segments), batch_size):
            batch = segments[i : i + batch_size]
            texts = [seg.text for seg in batch]

            raw = self._generate(build_batch_prompt(texts), max_output_tokens=2000)
            parts = parse_numbered_lines(raw)

            for j, seg in enumerate(batch):
                seg.translated = parts.get(j + 1) or seg.text

        return segments
