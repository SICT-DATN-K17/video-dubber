"""
app/extensions.py
Các extension dùng chung, khởi tạo rỗng ở đây rồi bind vào app trong create_app().
"""
from __future__ import annotations

import sqlite3

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
# storage mac dinh la bo nho trong tien trinh: moi container web dem rieng.
limiter = Limiter(key_func=get_remote_address, default_limits=[])

login_manager.login_view = "auth.login"
login_manager.login_message = "Vui lòng đăng nhập để tiếp tục."
login_manager.login_message_category = "info"


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    """SQLite bỏ qua khoá ngoại nếu không bật pragma cho từng kết nối.

    Không bật thì ON DELETE CASCADE lặng lẽ không chạy trên máy local và trong
    test, trong khi Postgres ở production vẫn chạy. Sai lệch kiểu này rất khó
    thấy vì nó không báo lỗi — chỉ để lại dữ liệu mồ côi.
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
