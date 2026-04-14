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


### Demo 1: Source Video

https://github.com/user-attachments/assets/458dfa22-e69a-4aa6-b86b-cb6ddb3e952f



### Demo 2: Dubbed Video (MarianMT)

https://github.com/user-attachments/assets/3c90c685-9d6f-4107-a983-cd66ad8e9376


## Recommended Repo Hygiene For Demo Videos

- If a video is larger than 100 MB, use Git LFS or attach it in GitHub Releases.
- Keep filenames stable after publishing links in README.
- For filenames with spaces, use percent-encoded links (for example, space becomes %20).

## Notes

- First run may be slower because Whisper/Transformers models are downloaded.
- MarianMT can run offline; OpenAI usually gives better translation quality.
- VietTTS setup may vary by package variant and environment.
