"""
app/permissions.py
Kiểm tra quyền ở phía server.

Giao diện có ẩn menu hay không là chuyện trình bày — ai cũng gọi thẳng API được,
nên quyền phải chặn ở đây.
"""
from __future__ import annotations

from functools import wraps

from flask import abort, jsonify, redirect, url_for
from flask_login import current_user

from app.models import Role


def require_role(*roles: str):
    """Chỉ cho phép các role được liệt kê. Trả JSON vì chỉ dùng cho /api."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Cần đăng nhập.", "code": 401}), 401
            if current_user.role not in roles:
                return jsonify({"error": "Bạn không có quyền thực hiện thao tác này.", "code": 403}), 403
            return view(*args, **kwargs)

        return wrapper

    return decorator


def require_admin_page(view):
    """Guard cho trang HTML. Khác require_admin ở chỗ trả trang lỗi 403 thay vì JSON."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapper


def require_admin(view):
    return require_role(Role.ADMIN)(view)
