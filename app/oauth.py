"""
app/oauth.py
Đăng nhập bằng tài khoản Google.

Chỉ xin ba phạm vi không nhạy cảm: openid, email, profile. Đăng nhập bằng
mật khẩu vẫn giữ nguyên — Google là lựa chọn thêm, không phải thay thế, để
lỡ OAuth trục trặc thì vẫn còn đường vào.
"""
from __future__ import annotations

import re
import secrets

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, flash, redirect, session, url_for
from flask_login import current_user, login_user

from app.extensions import db
from app.models import User
from config.settings import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

bp = Blueprint("oauth", __name__, url_prefix="/auth/google")

oauth = OAuth()

GOOGLE_DISCOVERY = "https://accounts.google.com/.well-known/openid-configuration"


def init_oauth(app) -> None:
    oauth.init_app(app)
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
        app.logger.info("Chưa cấu hình Google OAuth, bỏ qua.")
        return
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url=GOOGLE_DISCOVERY,
        client_kwargs={"scope": "openid email profile"},
    )


def is_enabled() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def _unique_username(email: str) -> str:
    """Sinh tên đăng nhập từ email, thêm hậu tố nếu đã có người dùng."""
    base = re.sub(r"[^a-z0-9._-]", "", (email.split("@")[0] or "").lower()) or "nguoidung"
    base = base[:40]
    candidate = base
    while User.query.filter_by(username=candidate).first():
        candidate = f"{base}-{secrets.token_hex(2)}"
    return candidate


@bp.get("/login")
def login():
    if not is_enabled():
        flash("Chưa bật đăng nhập bằng Google.", "danger")
        return redirect(url_for("auth.login"))
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    # Authlib tự sinh và kiểm tra state, chống CSRF cho vòng chuyển hướng.
    return oauth.google.authorize_redirect(url_for("oauth.callback", _external=True))


@bp.get("/callback")
def callback():
    if not is_enabled():
        return redirect(url_for("auth.login"))

    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        flash("Không đăng nhập được bằng Google, vui lòng thử lại.", "danger")
        return redirect(url_for("auth.login"))

    info = token.get("userinfo") or {}
    google_sub = info.get("sub")
    email = (info.get("email") or "").lower()
    if not google_sub:
        flash("Google không trả về thông tin tài khoản.", "danger")
        return redirect(url_for("auth.login"))

    # Khoá định danh là `sub` chứ không phải email: email đổi được, sub thì không.
    user = User.query.filter_by(google_sub=google_sub).first()

    if user is None and email and info.get("email_verified"):
        # Chỉ gộp với tài khoản sẵn có khi Google đã xác minh email — nếu không,
        # người khác có thể chiếm tài khoản bằng cách đăng ký trùng email.
        user = User.query.filter_by(email=email).first()
        if user:
            user.google_sub = google_sub

    # Kiểm tra khoá TRƯỚC khi tạo mới: giá trị mặc định của is_active chỉ được
    # gán lúc ghi xuống DB, nên user vừa dựng trong bộ nhớ vẫn còn None.
    if user is not None and not user.is_active:
        db.session.rollback()
        flash("Tài khoản đã bị khoá!", "danger")
        return redirect(url_for("auth.login"))

    if user is None:
        user = User(
            username=_unique_username(email),
            email=email or None,
            google_sub=google_sub,
            avatar_url=info.get("picture"),
            password_hash=None,
            is_active=True,
        )
        db.session.add(user)

    user.email = user.email or (email or None)
    user.avatar_url = info.get("picture") or user.avatar_url
    db.session.commit()

    login_user(user)
    session.permanent = True
    flash(f"Xin chào {user.username}!", "success")
    return redirect(url_for("main.index"))
