"""
app/errors.py
Chuẩn hoá lỗi: /api/* luôn trả JSON, phần còn lại giữ trang HTML.
"""
from __future__ import annotations

from flask import Flask, current_app, flash, jsonify, redirect, request, url_for
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException

from config.settings import MAX_UPLOAD_MB


def wants_json() -> bool:
    if request.path.startswith("/api/"):
        return True
    accept = request.accept_mimetypes
    return accept.accept_json and not accept.accept_html


def register_unauthorized_handler() -> None:
    """Flask-Login mặc định redirect sang trang login — với /api/* thì phải là 401 JSON."""
    from app.extensions import login_manager

    @login_manager.unauthorized_handler
    def unauthorized():
        if wants_json():
            return jsonify({"error": "Cần đăng nhập.", "code": 401}), 401
        flash(login_manager.login_message, login_manager.login_message_category)
        return redirect(url_for("auth.login"))


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(CSRFError)
    def handle_csrf_error(exc: CSRFError):
        if wants_json():
            return jsonify({"error": "Phiên làm việc đã hết hạn, vui lòng tải lại trang.", "code": 400}), 400
        flash("Phiên làm việc đã hết hạn, vui lòng thử lại.", "warning")
        target = "main.index" if current_user.is_authenticated else "auth.login"
        return redirect(url_for(target))

    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        if exc.code == 413:
            exc.description = f"File vượt quá giới hạn {MAX_UPLOAD_MB} MB."
        if wants_json():
            return jsonify({"error": exc.description, "code": exc.code}), exc.code
        return exc

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):
        if isinstance(exc, HTTPException):
            return exc
        current_app.logger.exception("Unhandled error on %s", request.path)
        if wants_json():
            return jsonify({"error": "Lỗi hệ thống, vui lòng thử lại.", "code": 500}), 500
        raise exc
