"""
wsgi.py
Điểm vào cho WSGI server và cho `flask` CLI.

    python wsgi.py                                    # development
    waitress-serve --listen=0.0.0.0:8000 wsgi:app     # production
    flask --app wsgi db upgrade                       # migration
    flask --app wsgi create-admin                     # tạo tài khoản admin
"""
from __future__ import annotations

from app import create_app
from app.jobs import mark_interrupted_jobs

app = create_app()


if __name__ == "__main__":
    # Job đang chạy dở lúc tiến trình trước bị tắt thì không ai hoàn thành nữa.
    try:
        mark_interrupted_jobs(app)
    except Exception:
        app.logger.warning("Bỏ qua bước dọn job dở: database chưa sẵn sàng (chạy 'flask --app wsgi db upgrade').")

    app.run(debug=True, use_reloader=False)
