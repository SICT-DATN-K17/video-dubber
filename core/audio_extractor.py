from __future__ import annotations

import subprocess
from pathlib import Path

from config.settings import FFPROBE_BIN, FFMPEG_BIN, TEMP_DIR


class AudioExtractor:
	"""Extract and inspect audio streams using ffmpeg/ffprobe."""

	def extract(self, video_path: str | Path, output_path: str | Path | None = None) -> Path:
		video_path = Path(video_path)
		if not video_path.exists():
			raise FileNotFoundError(f"Video not found: {video_path}")

		if output_path is None:
			output_path = TEMP_DIR / f"{video_path.stem}.wav"
		output_path = Path(output_path)
		output_path.parent.mkdir(parents=True, exist_ok=True)

		cmd = [
			FFMPEG_BIN,
			"-y",
			"-i",
			str(video_path),
			"-vn",
			"-ac",
			"1",
			"-ar",
			"16000",
			"-c:a",
			"pcm_s16le",
			str(output_path),
		]
		self._run(cmd, "Cannot extract audio. Check ffmpeg installation.")
		return output_path

	def get_duration(self, media_path: str | Path) -> float:
		media_path = Path(media_path)
		cmd = [
			FFPROBE_BIN,
			"-v",
			"error",
			"-show_entries",
			"format=duration",
			"-of",
			"default=noprint_wrappers=1:nokey=1",
			str(media_path),
		]
		completed = self._run(cmd, "Cannot read media duration. Check ffprobe installation.")
		return float(completed.stdout.strip() or 0)

	@staticmethod
	def _run(cmd: list[str], error_message: str) -> subprocess.CompletedProcess:
		try:
			return subprocess.run(cmd, capture_output=True, text=True, check=True)
		except FileNotFoundError as exc:
			raise RuntimeError(error_message) from exc
		except subprocess.CalledProcessError as exc:
			raise RuntimeError(f"{error_message}\n{exc.stderr.strip()}") from exc

