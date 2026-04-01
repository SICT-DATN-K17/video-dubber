"""
core/translator/marian_translator.py
Dịch EN → VI bằng MarianMT (Helsinki-NLP) — chạy offline, không cần API key.
"""
from __future__ import annotations

import re
from typing import List

from transformers import MarianMTModel, MarianTokenizer

from config.settings import MARIAN_MODEL_EN_VI, AI_PRESERVE_TERMS
from core.translator.base import BaseTranslator


# Pattern để bảo vệ thuật ngữ AI không bị dịch
_PLACEHOLDER_TMPL = "TERM{i}"
_TERM_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(t) for t in sorted(AI_PRESERVE_TERMS, key=len, reverse=True)) + r')\b',
    re.IGNORECASE,
)


def _protect_terms(text: str) -> tuple[str, dict]:
    """Thay thuật ngữ AI bằng placeholder trước khi dịch."""
    mapping = {}
    counter = [0]

    def replacer(match):
        ph = _PLACEHOLDER_TMPL.format(i=counter[0])
        mapping[ph] = match.group(0)
        counter[0] += 1
        return ph

    protected = _TERM_PATTERN.sub(replacer, text)
    return protected, mapping


def _restore_terms(text: str, mapping: dict) -> str:
    """Phục hồi thuật ngữ gốc từ placeholder."""
    for ph, original in mapping.items():
        text = text.replace(ph, original)
    return text


class MarianTranslator(BaseTranslator):
    """Dịch offline bằng Helsinki-NLP MarianMT (en → vi)."""

    def __init__(self, model_name: str = MARIAN_MODEL_EN_VI):
        print(f"[MarianMT] Đang tải model '{model_name}'...")
        self.tokenizer = MarianTokenizer.from_pretrained(model_name)
        self.model = MarianMTModel.from_pretrained(model_name)
        self._model_name = model_name
        print("[MarianMT] Tải xong!")

    @property
    def name(self) -> str:
        return "MarianMT (Helsinki-NLP, offline)"

    def translate_text(self, text: str) -> str:
        """Dịch một câu, bảo vệ thuật ngữ AI."""
        protected, mapping = _protect_terms(text)

        inputs = self.tokenizer(
            [protected],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        translated_tokens = self.model.generate(**inputs)
        translated = self.tokenizer.decode(
            translated_tokens[0],
            skip_special_tokens=True,
        )

        result = _restore_terms(translated, mapping)
        return result

    def translate_batch(self, texts: List[str]) -> List[str]:
        """Dịch nhiều câu cùng lúc (hiệu quả hơn vòng lặp đơn lẻ)."""
        protected_texts, mappings = [], []
        for t in texts:
            p, m = _protect_terms(t)
            protected_texts.append(p)
            mappings.append(m)

        inputs = self.tokenizer(
            protected_texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        translated_tokens = self.model.generate(**inputs)
        results = []
        for i, tokens in enumerate(translated_tokens):
            translated = self.tokenizer.decode(tokens, skip_special_tokens=True)
            results.append(_restore_terms(translated, mappings[i]))

        return results