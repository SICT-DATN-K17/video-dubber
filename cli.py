from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.pipeline import DubbingConfig, DubbingPipeline


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="AI Video Dubbing CLI (EN -> VI)")
	parser.add_argument("video", help="Path to input video file")
	parser.add_argument("--translator", choices=["openai", "marian"], default="marian")
	parser.add_argument("--openai-api-key", default="")
	parser.add_argument("--openai-model", default="gpt-4o-mini")
	parser.add_argument("--whisper-model", default="base")
	parser.add_argument("--tts-engine", choices=["edge-tts", "gtts"], default="edge-tts")
	parser.add_argument("--tts-voice", choices=["female", "male"], default="female")
	parser.add_argument("--original-volume", type=float, default=0.1)
	parser.add_argument("--subtitle-mode", choices=["bilingual", "vi", "en", "none"], default="bilingual")
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	video_path = Path(args.video)
	if not video_path.exists():
		print(f"[ERROR] Video not found: {video_path}")
		return 1

	cfg = DubbingConfig(
		translator_engine=args.translator,
		openai_api_key=args.openai_api_key,
		openai_model=args.openai_model,
		whisper_model=args.whisper_model,
		tts_engine=args.tts_engine,
		tts_voice=args.tts_voice,
		original_volume=args.original_volume,
		subtitle_mode=args.subtitle_mode,
	)

	pipeline = DubbingPipeline(cfg)
	result = pipeline.run(video_path)
	if not result.success:
		print(f"[ERROR] {result.error}")
		return 2

	print("[OK] Dubbing completed")
	print(f"Video: {result.output_video}")
	if result.srt_path:
		print(f"Subtitle: {result.srt_path}")
	print(f"Segments: {len(result.segments)}")
	print(f"Elapsed: {result.elapsed_seconds:.2f}s")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

