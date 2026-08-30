"""
app/extensions.py
Các extension dùng chung, khởi tạo rỗng ở đây rồi bind vào app trong create_app().
"""
from __future__ import annotations

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
# storage mac dinh la bo nho trong tien trinh: moi container web dem rieng.
limiter = Limiter(key_func=get_remote_address, default_limits=[])

login_manager.login_view = "auth.login"
login_manager.login_message = "Vui lòng đăng nhập để tiếp tục."
login_manager.login_message_category = "info"
