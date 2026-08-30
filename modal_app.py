"""
modal_app.py
Triển khai trên Modal: web chạy CPU, pipeline lồng tiếng chạy GPU.

    modal setup                       # một lần, để lấy token
    modal volume create dubber-data
    modal volume create dubber-models
    modal secret create video-dubber \\
        FLASK_SECRET_KEY=... DATABASE_URL=... GEMINI_API_KEY=... APP_ENV=production \\
        JOB_RUNNER=modal DATA_DIR=/data
    modal run modal_app.py::migrate   # tạo bảng trên Postgres
    modal deploy modal_app.py

Kiến trúc:
  web (CPU)  --spawn()-->  Dubber (GPU)  --ghi-->  Postgres + Volume
Web và GPU dùng chung một Volume cho file upload/kết quả, và chung một Postgres
để trao đổi tiến trình — nên web không cần chờ GPU, và request HTTP không bao giờ
chạm giới hạn 150 giây của Modal.
"""
from __future__ import annotations

import modal

APP_NAME = "video-dubber"

# Volume "data" giữ file upload + kết quả; volume "models" giữ trọng số model
# để container mới không phải tải lại (Whisper, MarianMT).
data_volume = modal.Volume.from_name("dubber-data", create_if_missing=True)
model_volume = modal.Volume.from_name("dubber-models", create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg")
    .pip_install_from_requirements("requirements.txt")
    .env(
        {
            # Model cache nằm trên volume, dùng lại giữa các lần chạy.
            "HF_HOME": "/models/huggingface",
            "XDG_CACHE_HOME": "/models/cache",
            "DATA_DIR": "/data",
            "JOB_RUNNER": "modal",
        }
    )
    .add_local_dir(".", remote_path="/root/app", ignore=["data", "*.mp4", ".git", "migrations/versions/__pycache__"])
)

app = modal.App(APP_NAME, image=image)
secrets = [modal.Secret.from_name("video-dubber")]

VOLUMES = {"/data": data_volume, "/models": model_volume}


@app.function(volumes=VOLUMES, secrets=secrets, min_containers=1, timeout=900)
@modal.concurrent(max_inputs=20)
@modal.wsgi_app()
def web():
    """Flask app hiện có, không sửa gì — chỉ bọc lại."""
    from wsgi import app as flask_app

    return flask_app


@app.cls(
    gpu="T4",
    volumes=VOLUMES,
    secrets=secrets,
    timeout=3600,
    scaledown_window=300,
    max_containers=2,
)
class Dubber:
    """Container GPU: nạp model một lần rồi phục vụ nhiều job."""

    @modal.enter()
    def load_models(self):
        # Nạp sẵn Whisper để job đầu tiên không phải chờ tải model.
        from config.settings import WHISPER_BACKEND  # noqa: F401
        from core.transcriber import Transcriber

        self.warm_transcriber = Transcriber(model_size="base", device="auto")
        print(f"[Modal] Container sẵn sàng, backend={self.warm_transcriber.backend}")

    @modal.method()
    def run(self, job_id: int, video_path: str, config_dict: dict) -> None:
        """Chạy một job. Tiến trình ghi thẳng vào Postgres cho web đọc."""
        from pathlib import Path

        from app import create_app
        from app.jobs import run_job
        from core.pipeline import DubbingConfig

        # Thấy được file mà container web vừa ghi lên volume.
        data_volume.reload()

        config_dict.pop("output_dir", None)
        config = DubbingConfig(**config_dict)

        flask_app = create_app()
        try:
            run_job(flask_app, job_id, Path(video_path), config)
        finally:
            # Đẩy video/SRT kết quả lên volume để container web phục vụ được.
            data_volume.commit()


@app.function(volumes=VOLUMES, secrets=secrets, timeout=600)
def migrate() -> None:
    """Chạy `flask db upgrade` trên Postgres trước mỗi lần deploy."""
    import subprocess

    subprocess.run(["flask", "--app", "wsgi", "db", "upgrade"], check=True, cwd="/root/app")


@app.local_entrypoint()
def main():
    """`modal run modal_app.py` — kiểm tra container GPU khởi động được."""
    print("Đang khởi động container GPU để kiểm tra...")
    Dubber().run.remote(0, "", {})
