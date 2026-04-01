"""
core/translator/openai_translator.py
Dịch EN → VI bằng OpenAI GPT, tối ưu cho thuật ngữ AI/ML.
"""
from __future__ import annotations

from typing import List

from openai import OpenAI

from config.settings import OPENAI_API_KEY, OPENAI_MODEL, AI_PRESERVE_TERMS
from core.translator.base import BaseTranslator
from core.transcriber import Segment


SYSTEM_PROMPT = """Bạn là chuyên gia dịch thuật tiếng Anh sang tiếng Việt, 
chuyên lĩnh vực Trí tuệ nhân tạo (AI) và Học máy (ML).

Quy tắc dịch:
1. Dịch tự nhiên, chuẩn ngữ pháp tiếng Việt.
2. Giữ nguyên các thuật ngữ kỹ thuật AI/ML bằng tiếng Anh (không dịch): 
   {preserve_terms}
3. Không thêm giải thích hay chú thích, chỉ trả về văn bản đã dịch.
4. Giữ nguyên dấu câu và cấu trúc câu gốc.
5. Dịch ngắn gọn, phù hợp để đọc thành lời nói.
""".format(preserve_terms=", ".join(AI_PRESERVE_TERMS[:20]))


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
        separator = " ||| "
        
        for i in range(0, len(segments), batch_size):
            batch = segments[i : i + batch_size]
            texts = [seg.text for seg in batch]
            combined = separator.join(texts)
            
            translated_combined = self.translate_text(
                f"Dịch từng câu sau, phân tách bằng ' ||| ':\n{combined}"
            )
            
            parts = [p.strip() for p in translated_combined.split("|||") if p.strip()]
            for j, seg in enumerate(batch):
                seg.translated = parts[j].strip() if j < len(parts) else seg.text

        return segments