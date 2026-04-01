from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable

from config.settings import FFMPEG_BIN, FFPROBE_BIN


def get_audio_duration(audio_path: str | Path) -> float:
	cmd = [
		FFPROBE_BIN,
		"-v",
		"error",
		"-show_entries",
		"format=duration",
		"-of",
		"default=noprint_wrappers=1:nokey=1",
		str(audio_path),
	]
	completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
	return float((completed.stdout or "0").strip() or 0)


def concat_audio(audio_paths: Iterable[str | Path], output_path: str | Path) -> Path:
	output_path = Path(output_path)
	output_path.parent.mkdir(parents=True, exist_ok=True)

	entries = [f"file '{Path(p).as_posix()}'" for p in audio_paths]
	if not entries:
		raise ValueError("No audio files provided for concatenation.")

	list_file = output_path.with_suffix(".txt")
	list_file.write_text("\n".join(entries), encoding="utf-8")
	cmd = [
		FFMPEG_BIN,
		"-y",
		"-f",
		"concat",
		"-safe",
		"0",
		"-i",
		str(list_file),
		"-c",
		"copy",
		str(output_path),
	]
	subprocess.run(cmd, capture_output=True, text=True, check=True)
	list_file.unlink(missing_ok=True)
	return output_path

