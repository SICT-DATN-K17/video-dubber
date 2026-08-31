"""
tests/conftest.py
Fixture dùng chung.

Vài biến môi trường phải đặt TRƯỚC khi import config.settings, vì module đó
đọc os.environ ngay lúc import chứ không phải lúc gọi.
"""
from __future__ import annotations

import os
import tempfile
import uuid

import pytest

_TMP_DIR = os.path.join(tempfile.gettempdir(), f"dubber_tests_{uuid.uuid4().hex}")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_TMP_DIR, "test.db").replace("\\", "/")
os.environ["DATA_DIR"] = _TMP_DIR
os.environ["GOOGLE_CLIENT_ID"] = "test-client-id"
os.environ["GOOGLE_CLIENT_SECRET"] = "test-secret"
os.makedirs(_TMP_DIR, exist_ok=True)

from app import create_app  # noqa: E402
from app.extensions import db as _db  # noqa: E402
from app.models import Job, JobStatus, Role, User  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

PASSWORD = "pw123456"


@pytest.fixture()
def app():
    """App sạch cho mỗi test: CSRF và rate limit tắt sẵn.

    Test nào cần hai thứ đó thì bật lại trong chính test ấy.
    """
    application = create_app(
        {"TESTING": True, "WTF_CSRF_ENABLED": False, "RATELIMIT_ENABLED": False}
    )
    with application.app_context():
        _db.drop_all()
        _db.create_all()
    yield application
    with application.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db(app):
    with app.app_context():
        yield _db


@pytest.fixture()
def client(app):
    return app.test_client()


def make_user(username: str, *, role: str = Role.USER, google: bool = False, **kwargs) -> User:
    user = User(
        username=username,
        password_hash=None if google else generate_password_hash(PASSWORD),
        role=role,
        is_active=kwargs.pop("is_active", True),
        **kwargs,
    )
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture()
def user(app):
    with app.app_context():
        created = make_user("alice")
        return created.id


@pytest.fixture()
def other_user(app):
    with app.app_context():
        created = make_user("bob")
        return created.id


@pytest.fixture()
def admin(app):
    with app.app_context():
        created = make_user("boss", role=Role.ADMIN)
        return created.id


def login(app, username: str, password: str = PASSWORD):
    """Trả về client đã đăng nhập sẵn."""
    c = app.test_client()
    c.post("/login", data={"username": username, "password": password})
    return c


@pytest.fixture()
def as_user(app, user):
    return login(app, "alice")


@pytest.fixture()
def as_other(app, other_user):
    return login(app, "bob")


@pytest.fixture()
def as_admin(app, admin):
    return login(app, "boss")


def make_job(user_id: int, **kwargs) -> Job:
    defaults = {
        "status": JobStatus.DONE,
        "progress": 100,
        "message": "xong",
        "source_filename": "bai-giang.mp4",
        "translator_engine": "marian",
    }
    defaults.update(kwargs)
    job = Job(user_id=user_id, **defaults)
    _db.session.add(job)
    _db.session.commit()
    return job
