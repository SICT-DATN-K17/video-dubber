from __future__ import annotations

import os
import importlib
from pathlib import Path

try:
	dotenv = importlib.import_module("dotenv")
	dotenv.load_dotenv()
except Exception:
	# dotenv is optional; environment variables can still be provided by shell.
	pass


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"
TEMP_DIR = DATA_DIR / "temp"

for directory in (DATA_DIR, UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR):
	directory.mkdir(parents=True, exist_ok=True)


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

MARIAN_MODEL_EN_VI = os.getenv("MARIAN_MODEL_EN_VI", "pNam1802/marian-finetuned-ai-vi")
HF_TOKEN = os.getenv("HF_TOKEN", os.getenv("HUGGINGFACE_TOKEN", "")).strip()

AI_PRESERVE_TERMS = [
	"AI",
	"ML",
	"Deep Learning",
	"Machine Learning",
	"Neural Network",
	"Transformer",
	"LLM",
	"GPU",
	"CPU",
	"Prompt",
	"Fine-tuning",
	"RAG",
	"Embeddings",
	"Token",
	"Inference",
	"Dataset",
	"OpenAI",
	"Google",
	"Microsoft",
	"PyTorch",
	"TensorFlow",
]

FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")
FFPROBE_BIN = os.getenv("FFPROBE_BIN", "ffprobe")

