"""
app/admin.py
API quản trị: xem người dùng, đổi quyền, khoá tài khoản, thống kê chi phí.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.models import Job, JobStatus, Role, User
from app.permissions import require_admin
from app.quota import get_usage

bp = Blueprint("admin", __name__, url_prefix="/api")


@bp.get("/usage")
@login_required
def my_usage():
    """Mức tiêu thụ của chính người đang đăng nhập."""
    return jsonify(get_usage(current_user).as_dict())


@bp.get("/admin/users")
@login_required
@require_admin
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    rows = []
    for user in users:
        usage = get_usage(user)
        rows.append(
            {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "quota_jobs_per_day": user.quota_jobs_per_day,
                "usage": usage.as_dict(),
            }
        )
    return jsonify({"users": rows, "total": len(rows)})


@bp.patch("/admin/users/<int:user_id>")
@login_required
@require_admin
def update_user(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "Không tìm thấy tài khoản.", "code": 404}), 404

    payload = request.get_json(silent=True) or {}

    if "role" in payload:
        role = payload["role"]
        if role not in (Role.USER, Role.ADMIN):
            return jsonify({"error": "Role không hợp lệ.", "code": 400}), 400
        if user.id == current_user.id and role != Role.ADMIN:
            return jsonify({"error": "Không thể tự hạ quyền của chính mình.", "code": 400}), 400
        user.role = role

    if "is_active" in payload:
        is_active = bool(payload["is_active"])
        if user.id == current_user.id and not is_active:
            return jsonify({"error": "Không thể tự khoá tài khoản của chính mình.", "code": 400}), 400
        user.is_active = is_active

    if "quota_jobs_per_day" in payload:
        value = payload["quota_jobs_per_day"]
        if value is not None and (not isinstance(value, int) or value < 0):
            return jsonify({"error": "Hạn mức phải là số nguyên không âm.", "code": 400}), 400
        user.quota_jobs_per_day = value

    db.session.commit()
    return jsonify({"id": user.id, "username": user.username, "role": user.role, "is_active": user.is_active})


@bp.get("/admin/stats")
@login_required
@require_admin
def stats():
    """Số liệu cho dashboard: tổng quan, chi phí, và 14 ngày gần nhất."""
    since = datetime.now(timezone.utc) - timedelta(days=14)

    totals = db.session.query(
        func.count(Job.id),
        func.coalesce(func.sum(Job.elapsed_sec), 0.0),
        func.coalesce(func.sum(Job.estimated_cost_usd), 0.0),
        func.coalesce(func.avg(Job.elapsed_sec), 0.0),
    ).one()

    by_status = dict(
        db.session.query(Job.status, func.count(Job.id)).group_by(Job.status).all()
    )
    by_engine = dict(
        db.session.query(Job.translator_engine, func.count(Job.id))
        .filter(Job.translator_engine.isnot(None))
        .group_by(Job.translator_engine)
        .all()
    )

    daily = (
        db.session.query(
            func.date(Job.created_at).label("day"),
            func.count(Job.id),
            func.coalesce(func.sum(Job.estimated_cost_usd), 0.0),
        )
        .filter(Job.created_at >= since)
        .group_by("day")
        .order_by("day")
        .all()
    )

    top_users = (
        db.session.query(
            User.username,
            func.count(Job.id),
            func.coalesce(func.sum(Job.estimated_cost_usd), 0.0),
        )
        .join(Job, Job.user_id == User.id)
        .group_by(User.username)
        .order_by(func.coalesce(func.sum(Job.estimated_cost_usd), 0.0).desc())
        .limit(10)
        .all()
    )

    done = by_status.get(JobStatus.DONE, 0)
    return jsonify(
        {
            "totals": {
                "jobs": totals[0],
                "gpu_seconds": round(float(totals[1]), 1),
                "estimated_cost_usd": round(float(totals[2]), 4),
                "avg_seconds_per_job": round(float(totals[3]), 1),
                "success_rate": round(done / totals[0] * 100, 1) if totals[0] else 0.0,
                "users": User.query.count(),
            },
            "by_status": by_status,
            "by_engine": by_engine,
            "daily": [
                {"day": str(day), "jobs": count, "estimated_cost_usd": round(float(cost), 4)}
                for day, count, cost in daily
            ],
            "top_users": [
                {"username": name, "jobs": count, "estimated_cost_usd": round(float(cost), 4)}
                for name, count, cost in top_users
            ],
            "note": (
                "estimated_cost_usd chỉ tính thời gian pipeline chạy. Hoá đơn Modal thực tế "
                "cao hơn vì còn tính container nằm không, cold start, CPU, RAM và container web."
            ),
        }
    )
