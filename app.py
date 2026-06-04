import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from config.settings import OPENAI_API_KEY, OPENAI_MODEL, OUTPUT_DIR, UPLOAD_DIR, DATA_DIR
from core.pipeline import DubbingConfig, DubbingPipeline


ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ALLOWED_TRANSLATORS = {"openai", "marian"}
ALLOWED_WHISPER_MODELS = {"tiny", "base", "small", "medium", "large"}
ALLOWED_DEVICES = {"auto", "cuda", "cpu"}
ALLOWED_TTS_ENGINES = {"edge-tts", "gtts"}
ALLOWED_VOICES = {"female", "male"}
ALLOWED_SUBTITLE_MODES = {"bilingual", "vi", "en", "none"}

# Keep in-memory JOBS for progress updates since progress doesn't need to be persisted
JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-change-this-secret")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "2048")) * 1024 * 1024

# Database Setup
db_path = DATA_DIR / "database.db"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    jobs = db.relationship('Job', backref='user', lazy=True)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_name = db.Column(db.String(255), nullable=False)
    video_url = db.Column(db.String(255), nullable=False)
    srt_name = db.Column(db.String(255), nullable=True)
    srt_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- Helpers ---
def _update_job(job_id: str, **kwargs: Any) -> None:
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(kwargs)


def _run_pipeline_job(job_id: str, user_id: int, video_path: Path, config: DubbingConfig) -> None:
    def on_progress(percent: int, message: str) -> None:
        _update_job(job_id, progress=percent, message=message, status="processing")

    pipeline = DubbingPipeline(config)
    result = pipeline.run(video_path, progress_cb=on_progress)

    if result.success and result.output_video:
        output_name = result.output_video.name
        srt_name = result.srt_path.name if result.srt_path else None
        video_url = f"/media/output/{quote(output_name)}"
        srt_url = f"/media/output/{quote(srt_name)}" if srt_name else None
        
        # Save to DB inside app context
        with app.app_context():
            new_job = Job(
                user_id=user_id,
                video_name=output_name,
                video_url=video_url,
                srt_name=srt_name,
                srt_url=srt_url
            )
            db.session.add(new_job)
            db.session.commit()

        _update_job(
            job_id,
            status="done",
            progress=100,
            message="Hoan tat xu ly video.",
            result={
                "video_name": output_name,
                "video_url": video_url,
                "srt_name": srt_name,
                "srt_url": srt_url,
                "elapsed_seconds": round(result.elapsed_seconds, 2),
            },
        )
    else:
        _update_job(
            job_id,
            status="failed",
            progress=0,
            message=result.error or "Xu ly that bai.",
            result=None,
        )

    try:
        video_path.unlink(missing_ok=True)
    except OSError:
        pass


def _recent_outputs(limit: int = 8) -> list[dict[str, str | None]]:
    if not current_user.is_authenticated:
        return []
    
    recent_jobs = Job.query.filter_by(user_id=current_user.id).order_by(Job.created_at.desc()).limit(limit).all()
    rows = []
    for job in recent_jobs:
        rows.append({
            "video_name": job.video_name,
            "video_url": job.video_url,
            "srt_name": job.srt_name,
            "srt_url": job.srt_url
        })
    return rows


# --- Routes ---
@app.route("/login", methods=["GET", "POST"])
def login() -> str:
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Đăng nhập thành công!", "success")
            return redirect(url_for("index"))
        flash("Sai thông tin đăng nhập!", "danger")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register() -> str:
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            flash("Vui lòng điền đủ!", "danger")
            return render_template("register.html")
            
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Tên đăng nhập đã tồn tại!", "danger")
        else:
            new_user = User(username=username, password_hash=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            
            login_user(new_user)
            flash("Đăng ký thành công!", "success")
            return redirect(url_for("index"))

    return render_template("register.html")

@app.route("/logout", methods=["POST"])
@login_required
def logout() -> str:
    logout_user()
    flash("Đã đăng xuất!", "info")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index() -> str:
    return render_template(
        "index.html",
        outputs=_recent_outputs(),
        openai_key_exists=bool(OPENAI_API_KEY),
        default_openai_model=OPENAI_MODEL,
    )


@app.post("/api/upload")
@login_required
def upload_video():
    video = request.files.get("video")
    if not video or not video.filename:
        return jsonify({"error": "Vui long chon file video."}), 400

    ext = Path(video.filename).suffix.lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        return jsonify({"error": "Dinh dang video khong duoc ho tro."}), 400

    translator_engine = request.form.get("translator_engine", "marian")
    if translator_engine not in ALLOWED_TRANSLATORS:
        translator_engine = "marian"

    openai_api_key = request.form.get("openai_api_key", "").strip() or OPENAI_API_KEY
    if translator_engine == "openai" and not openai_api_key:
        return jsonify({"error": "Can OPENAI API key de dung OpenAI translator."}), 400

    safe_name = secure_filename(video.filename)
    upload_path = UPLOAD_DIR / f"{uuid.uuid4().hex}_{safe_name}"
    video.save(upload_path)

    whisper_model = request.form.get("whisper_model", "base")
    if whisper_model not in ALLOWED_WHISPER_MODELS:
        whisper_model = "base"

    compute_device = request.form.get("compute_device", "auto")
    if compute_device not in ALLOWED_DEVICES:
        compute_device = "auto"

    tts_engine = request.form.get("tts_engine", "edge-tts")
    if tts_engine not in ALLOWED_TTS_ENGINES:
        tts_engine = "edge-tts"

    tts_voice = request.form.get("tts_voice", "female")
    if tts_voice not in ALLOWED_VOICES:
        tts_voice = "female"

    subtitle_mode = request.form.get("subtitle_mode", "bilingual")
    if subtitle_mode not in ALLOWED_SUBTITLE_MODES:
        subtitle_mode = "bilingual"

    try:
        original_volume = float(request.form.get("original_volume", "10"))
    except ValueError:
        original_volume = 10.0
    original_volume = max(0.0, min(50.0, original_volume)) / 100.0

    config = DubbingConfig(
        translator_engine=translator_engine,
        openai_api_key=openai_api_key,
        openai_model=request.form.get("openai_model", OPENAI_MODEL),
        whisper_model=whisper_model,
        compute_device=compute_device,
        tts_engine=tts_engine,
        tts_voice=tts_voice,
        original_volume=original_volume,
        subtitle_mode=subtitle_mode,
    )

    job_id = uuid.uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {
            "status": "queued",
            "progress": 1,
            "message": "Da nhan video, dang khoi tao tac vu...",
            "result": None,
        }

    # Pass current_user.id so the worker thread can insert the Job correct into the DB
    worker = threading.Thread(target=_run_pipeline_job, args=(job_id, current_user.id, upload_path, config), daemon=True)
    worker.start()
    return jsonify({"job_id": job_id})


@app.get("/api/progress/<job_id>")
@login_required
def job_progress(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Khong tim thay job."}), 404
    return jsonify(job)


@app.get("/media/output/<path:filename>")
@login_required
def serve_output(filename: str):
    user_id = current_user.id
    # Check if the requested file belongs to the current user
    # Note: srt files and video files are tracked with different columns. We check if either matches.
    job = Job.query.filter(
        (Job.user_id == user_id) & 
        ((Job.video_name == filename) | (Job.srt_name == filename))
    ).first()
    
    if not job:
        # Prevent unauthorized access
        return "Ban khong co quyen truy cap hoac file khong ton tai", 403

    return send_from_directory(OUTPUT_DIR, filename, as_attachment=False)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
