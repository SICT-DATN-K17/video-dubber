# AI Video Dubbing (EN to VI)

End-to-end pipeline to dub English videos into Vietnamese, with subtitle export and both UI/CLI workflows.

## Project Overview

This project automates the full dubbing process:
1. Extract audio from video with ffmpeg
2. Transcribe speech to text with Whisper
3. Translate EN to VI with OpenAI or MarianMT
4. Synthesize Vietnamese speech with edge-tts, gTTS, or VietTTS
5. Compose dubbed audio back into the original video
6. Export video and SRT subtitles

Supported usage modes:
- Streamlit application for interactive usage
- CLI for scripted or batch workflows

## Tech Stack

- Python 3.10+
- ffmpeg, ffprobe
- openai-whisper
- transformers + torch
- edge-tts, gTTS
- yt-dlp (optional for download workflows)

## Installation

Prerequisites:
- Python 3.10 or newer
- ffmpeg and ffprobe available in PATH

Setup:

	pip install -r requirements.txt
	copy .env.example .env

If using OpenAI translation, set OPENAI_API_KEY in .env.

## Run The App

Start Streamlit UI:

	streamlit run app.py

Run from CLI:

	python cli.py path/to/video.mp4 --translator marian

OpenAI translation example:

	python cli.py path/to/video.mp4 --translator openai --openai-api-key sk-...

VietTTS example:

	python cli.py path/to/video.mp4 --tts-engine viettts

## Output Artifacts

- Dubbed video: data/outputs/*_dubbed.mp4
- Subtitle file: data/outputs/*_dubbed.srt

## Demo Videos

Current repository includes 2 demo videos:
- [What is Reinforcement Learning- - AI Basics - YouTube.mp4](What%20is%20Reinforcement%20Learning-%20-%20AI%20Basics%20-%20YouTube.mp4)
- [mariantMT-reinforcementLearning.mp4](mariantMT-reinforcementLearning.mp4)

Click-to-watch links:
- [Watch Demo 1 (Source)](./What%20is%20Reinforcement%20Learning-%20-%20AI%20Basics%20-%20YouTube.mp4)
- [Watch Demo 2 (Dubbed MarianMT)](./mariantMT-reinforcementLearning.mp4)

Inline player block (works on platforms that allow HTML video in README):

<h3>Demo 1 - Source Video</h3>
<video src="./What%20is%20Reinforcement%20Learning-%20-%20AI%20Basics%20-%20YouTube.mp4" controls width="860"></video>

<h3>Demo 2 - Dubbed Result (MarianMT)</h3>
<video src="./mariantMT-reinforcementLearning.mp4" controls width="860"></video>

If inline video is blocked by your platform, use the watch links above.

## Recommended Repo Hygiene For Demo Videos

- If a video is larger than 100 MB, use Git LFS or attach it in GitHub Releases.
- Keep filenames stable after publishing links in README.
- For filenames with spaces, use percent-encoded links (for example, space becomes %20).

## Notes

- First run may be slower because Whisper/Transformers models are downloaded.
- MarianMT can run offline; OpenAI usually gives better translation quality.
- VietTTS setup may vary by package variant and environment.