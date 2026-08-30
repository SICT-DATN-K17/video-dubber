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
    # add_local_* phai la lop CUOI CUNG — Modal cam moi build step sau no.
    # Mount vao /root vi do la thu muc lam viec mac dinh cua container;
    # de o cho khac thi `from wsgi import app` se khong tim thay module.
    .add_local_dir(
        ".",
        remote_path="/root",
        ignore=[
            ".env*",          # KHONG bao gio dong goi secret vao image
            "!.env.example",
            ".git/**",
            "data/**",
            "design/**",   # mockup tu Stitch, khong can trong image
            "**/__pycache__/**",
            "**/*.pyc",
            "*.mp4",
            "*.wav",
            ".venv/**",
            "venv/**",
        ],
    )
)

# Bien moi truong dat o muc function (chi ton tai luc chay), KHONG dat trong
# image: HF_HOME/XDG_CACHE_HOME tro vao /models, ma neu image co san /models
# thi Modal tu choi mount volume vao thu muc khong rong.
RUNTIME_ENV = {
    "HF_HOME": "/models/huggingface",
    "XDG_CACHE_HOME": "/models/cache",
    "DATA_DIR": "/data",
    "JOB_RUNNER": "modal",
}

app = modal.App(APP_NAME, image=image)
# Nhieu secret gop lai thanh mot tap bien moi truong. Tach rieng key Google
# de khong phai nhap lai DATABASE_URL moi lan doi key.
secrets = [
    modal.Secret.from_name("video-dubber"),
    modal.Secret.from_name("googlecloud-secret"),
]

VOLUMES = {"/data": data_volume, "/models": model_volume}


# Khong dat min_containers: container web luon-chay bi tinh tien 24/7 (~$4-6/thang)
# du khong ai dung. Doi lai lan truy cap dau tien sau luc rieng phai cho container
# khoi dong vai giay. Voi du an demo thi danh doi nay dang gia.
@app.function(volumes=VOLUMES, secrets=secrets, env=RUNTIME_ENV, timeout=900)
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
    env=RUNTIME_ENV,
    timeout=3600,
    # Sau job cuoi, container GPU con song them bang nay giay va VAN TINH TIEN.
    # 300s idle ton gap ~20 lan chinh 13s xu ly that. 60s du de gom cac job lien tiep.
    scaledown_window=60,
    # Tran chi tieu: toi da 1 container T4 cung luc, job den sau se xep hang.
    max_containers=1,
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


@app.function(volumes=VOLUMES, secrets=secrets, env=RUNTIME_ENV, timeout=600)
def migrate() -> None:
    """Chạy `flask db upgrade` trên Postgres trước mỗi lần deploy."""
    import subprocess

    subprocess.run(["flask", "--app", "wsgi", "db", "upgrade"], check=True, cwd="/root")


@app.local_entrypoint()
def main():
    """`modal run modal_app.py` — kiểm tra container GPU khởi động được."""
    print("Đang khởi động container GPU để kiểm tra...")
    Dubber().run.remote(0, "", {})
