"""
core/translator/llm_common.py
Prompt và tiện ích dùng chung cho các translator dựa trên LLM (OpenAI, Gemini...).
"""
from __future__ import annotations

from typing import Dict, List

from config.settings import AI_PRESERVE_TERMS


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


def build_batch_prompt(texts: List[str]) -> str:
    """Ghép nhiều câu thành 1 prompt đánh số để dịch trong một request."""
    numbered = "\n".join(f"{idx+1}. {t}" for idx, t in enumerate(texts))
    return (
        f"Dịch {len(texts)} câu sau từ tiếng Anh sang tiếng Việt.\n"
        f"Trả về đúng {len(texts)} dòng, mỗi dòng bắt đầu bằng số thứ tự tương ứng "
        f"(ví dụ: '1. ...', '2. ...'). Không thêm hoặc bỏ dòng nào.\n\n"
        f"{numbered}"
    )


def parse_numbered_lines(raw: str) -> Dict[int, str]:
    """Tách kết quả dạng '1. ...' / '1) ...' thành dict {số thứ tự: bản dịch}."""
    parts: Dict[int, str] = {}
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        for sep in (". ", ") "):
            if line[0].isdigit() and sep in line:
                idx_str, _, translation = line.partition(sep)
                try:
                    parts[int(idx_str.strip())] = translation.strip()
                except ValueError:
                    pass
                break
    return parts
