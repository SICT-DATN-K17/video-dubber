"""
app/models.py
Schema: User và Job. Job là nguồn sự thật duy nhất về trạng thái xử lý —
không còn dict trong RAM, nên restart server không làm mất job.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flask_login import UserMixin

from app.extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobStatus:
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"

    #: Trạng thái chưa kết thúc — dùng để dò job mồ côi sau khi restart.
    ACTIVE = (QUEUED, PROCESSING)


class Role:
    USER = "user"
    ADMIN = "admin"


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.USER, server_default=Role.USER)
    # Flask-Login đọc thuộc tính is_active để quyết định có cho đăng nhập không.
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    jobs = db.relationship("Job", backref="user", lazy=True, cascade="all, delete-orphan")

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"


class Job(db.Model):
    __tablename__ = "job"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    # ── Trạng thái ────────────────────────────────────────────
    status = db.Column(
        db.String(20), nullable=False, default=JobStatus.QUEUED, server_default=JobStatus.QUEUED, index=True
    )
    progress = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    message = db.Column(db.String(500), nullable=False, default="", server_default="")
    error = db.Column(db.Text, nullable=True)

    # ── Đầu vào ───────────────────────────────────────────────
    source_filename = db.Column(db.String(255), nullable=True)
    file_size = db.Column(db.BigInteger, nullable=True)
    translator_engine = db.Column(db.String(30), nullable=True)
    tts_engine = db.Column(db.String(30), nullable=True)
    whisper_model = db.Column(db.String(30), nullable=True)

    # ── Kết quả ───────────────────────────────────────────────
    video_name = db.Column(db.String(255), nullable=True)
    video_url = db.Column(db.String(500), nullable=True)
    srt_name = db.Column(db.String(255), nullable=True)
    srt_url = db.Column(db.String(500), nullable=True)
    duration_sec = db.Column(db.Float, nullable=True)
    elapsed_sec = db.Column(db.Float, nullable=True)
    segment_count = db.Column(db.Integer, nullable=True)

    # ── Modal (dùng từ Phase 2) ───────────────────────────────
    modal_call_id = db.Column(db.String(100), nullable=True, index=True)

    # ── Mốc thời gian ─────────────────────────────────────────
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)

    @property
    def is_finished(self) -> bool:
        return self.status not in JobStatus.ACTIVE

    def to_progress_dict(self) -> dict[str, Any]:
        """Payload cho endpoint theo dõi tiến trình."""
        result = None
        if self.status == JobStatus.DONE and self.video_url:
            result = {
                "video_name": self.video_name,
                "video_url": self.video_url,
                "srt_name": self.srt_name,
                "srt_url": self.srt_url,
                "elapsed_seconds": round(self.elapsed_sec or 0, 2),
            }
        return {
            "job_id": self.id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "result": result,
        }

    def __repr__(self) -> str:
        return f"<Job {self.id} {self.status} {self.progress}%>"
