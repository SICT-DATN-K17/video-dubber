"""
app/api.py
Endpoint JSON cho upload và theo dõi tiến trình.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.extensions import db, limiter
from app.jobs import start_job
from app.models import Job, JobStatus
from app.quota import check_quota
from app.storage import commit_uploads
from config.settings import (
    RATELIMIT_UPLOAD,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    UPLOAD_DIR,
)
from core.pipeline import DubbingConfig

bp = Blueprint("api", __name__, url_prefix="/api")

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ALLOWED_TRANSLATORS = {"openai", "gemini", "marian"}
ALLOWED_WHISPER_MODELS = {"tiny", "base", "small", "medium", "large"}
ALLOWED_DEVICES = {"auto", "cuda", "cpu"}
ALLOWED_TTS_ENGINES = {"edge-tts", "gtts"}
ALLOWED_VOICES = {"female", "male"}
ALLOWED_SUBTITLE_MODES = {"bilingual", "vi", "en", "none"}


def _pick(field: str, allowed: set[str], default: str) -> str:
    value = request.form.get(field, default)
    return value if value in allowed else default


@bp.post("/upload")
@login_required
@limiter.limit(RATELIMIT_UPLOAD)
def upload_video():
    video = request.files.get("video")
    if not video or not video.filename:
        return jsonify({"error": "Vui lòng chọn file video."}), 400

    ext = Path(video.filename).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        return jsonify({"error": "Định dạng video không được hỗ trợ."}), 400

    translator_engine = _pick("translator_engine", ALLOWED_TRANSLATORS, "marian")

    openai_api_key = request.form.get("openai_api_key", "").strip() or OPENAI_API_KEY
    if translator_engine == "openai" and not openai_api_key:
        return jsonify({"error": "Cần OPENAI API key để dùng OpenAI translator."}), 400

    gemini_api_key = request.form.get("gemini_api_key", "").strip() or GEMINI_API_KEY
    if translator_engine == "gemini" and not gemini_api_key:
        return jsonify({"error": "Cần GEMINI API key để dùng Gemini translator."}), 400

    whisper_model = _pick("whisper_model", ALLOWED_WHISPER_MODELS, "base")
    compute_device = _pick("compute_device", ALLOWED_DEVICES, "auto")
    tts_engine = _pick("tts_engine", ALLOWED_TTS_ENGINES, "edge-tts")
    tts_voice = _pick("tts_voice", ALLOWED_VOICES, "female")
    subtitle_mode = _pick("subtitle_mode", ALLOWED_SUBTITLE_MODES, "bilingual")

    try:
        original_volume = float(request.form.get("original_volume", "10"))
    except ValueError:
        original_volume = 10.0
    original_volume = max(0.0, min(50.0, original_volume)) / 100.0

    # Kiem tra han muc TRUOC khi ghi file: khong de mot nguoi vuot quota
    # van kip do day dia bang cac file rac.
    allowed, reason = check_quota(current_user, request.content_length or 0)
    if not allowed:
        return jsonify({"error": reason, "code": 429}), 429

    safe_name = secure_filename(video.filename)
    upload_path = UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe_name}"
    video.save(upload_path)

    # Container GPU doc file nay qua Volume nen phai commit truoc khi spawn.
    commit_uploads()

    job = Job(
        user_id=current_user.id,
        status=JobStatus.QUEUED,
        progress=1,
        message="Đã nhận video, đang khởi tạo tác vụ...",
        source_filename=video.filename,
        file_size=upload_path.stat().st_size,
        translator_engine=translator_engine,
        tts_engine=tts_engine,
        whisper_model=whisper_model,
    )
    db.session.add(job)
    db.session.commit()

    config = DubbingConfig(
        translator_engine=translator_engine,
        openai_api_key=openai_api_key,
        openai_model=request.form.get("openai_model", OPENAI_MODEL) or OPENAI_MODEL,
        gemini_api_key=gemini_api_key,
        gemini_model=request.form.get("gemini_model", GEMINI_MODEL) or GEMINI_MODEL,
        whisper_model=whisper_model,
        compute_device=compute_device,
        tts_engine=tts_engine,
        tts_voice=tts_voice,
        original_volume=original_volume,
        subtitle_mode=subtitle_mode,
    )

    start_job(current_app._get_current_object(), job.id, upload_path, config)
    return jsonify({"job_id": job.id}), 202


@bp.get("/progress/<int:job_id>")
@login_required
def job_progress(job_id: int):
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if job is None:
        return jsonify({"error": "Không tìm thấy job."}), 404
    return jsonify(job.to_progress_dict())
