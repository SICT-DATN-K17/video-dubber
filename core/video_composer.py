from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from config.settings import FFMPEG_BIN, FFMPEG_TIMEOUT, OUTPUT_DIR, TEMP_DIR
from utils.proc import run_command
from core.transcriber import Segment


class VideoComposer:
	"""Compose final dubbed video by delaying and mixing per-segment TTS audio."""

	def compose(
		self,
		video_path: str | Path,
		segments: List[Segment],
		tts_paths: List[str | Path],
		original_volume: float = 0.1,
		tts_volume: float = 1.6,
		video_duration: Optional[float] = None,
	) -> Path:
		video_path = Path(video_path)
		if not video_path.exists():
			raise FileNotFoundError(f"Video not found: {video_path}")
		if not tts_paths:
			raise ValueError("No TTS files provided to compose output video.")

		OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
		out_path = OUTPUT_DIR / f"{video_path.stem}_dubbed.mp4"

		cmd = [FFMPEG_BIN, "-y", "-i", str(video_path)]
		normalized_tts = [Path(p) for p in tts_paths]
		for p in normalized_tts:
			cmd += ["-i", str(p)]

		filter_parts = [f"[0:a]volume={original_volume}[orig]"]
		mix_inputs = ["[orig]"]

		limit = min(len(segments), len(normalized_tts))
		for idx in range(limit):
			delay_ms = max(0, int(segments[idx].start * 1000))
			label = f"t{idx}"
			filter_parts.append(
				f"[{idx + 1}:a]volume={tts_volume},adelay={delay_ms}|{delay_ms}[{label}]"
			)
			mix_inputs.append(f"[{label}]")

		filter_parts.append(
			"".join(mix_inputs)
			+ f"amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=2:normalize=0[mix_raw]"
		)
		# Limit peaks after boosting TTS to avoid clipping while keeping loudness stable.
		filter_parts.append("[mix_raw]alimiter=limit=0.95[mix]")
		filter_complex = ";".join(filter_parts)

		cmd += [
			"-filter_complex",
			filter_complex,
			"-map",
			"0:v",
			"-map",
			"[mix]",
			"-c:v",
			"copy",
			"-c:a",
			"aac",
			"-shortest",
			str(out_path),
		]

		run_command(
			cmd,
			timeout=FFMPEG_TIMEOUT,
			error_message="Video compose failed. Check ffmpeg installation.",
		)
		return out_path

