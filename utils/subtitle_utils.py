from __future__ import annotations

from pathlib import Path
from typing import Iterable

from core.transcriber import Segment


def _fmt_srt_time(seconds: float) -> str:
	ms_total = int(max(0.0, seconds) * 1000)
	hours = ms_total // 3_600_000
	minutes = (ms_total % 3_600_000) // 60_000
	secs = (ms_total % 60_000) // 1000
	ms = ms_total % 1000
	return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def segments_to_srt(
	segments: Iterable[Segment],
	mode: str = "bilingual",
	output_path: str | Path | None = None,
) -> str:
	lines: list[str] = []
	seg_list = list(segments)

	for idx, seg in enumerate(seg_list, start=1):
		lines.append(str(idx))
		lines.append(f"{_fmt_srt_time(seg.start)} --> {_fmt_srt_time(seg.end)}")

		en_text = (seg.text or "").strip()
		vi_text = (seg.translated or "").strip()

		if mode == "en":
			lines.append(en_text)
		elif mode == "vi":
			lines.append(vi_text or en_text)
		else:
			if en_text:
				lines.append(en_text)
			if vi_text:
				lines.append(vi_text)

		lines.append("")

	content = "\n".join(lines).strip() + "\n"
	if output_path is not None:
		output_path = Path(output_path)
		output_path.parent.mkdir(parents=True, exist_ok=True)
		output_path.write_text(content, encoding="utf-8")
	return content

