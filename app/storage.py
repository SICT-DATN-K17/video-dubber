"""
app/storage.py
Đồng bộ file giữa container web và container GPU khi chạy trên Modal.

Modal Volume không tự đồng bộ hai chiều: bên ghi phải commit(), bên đọc phải
reload() thì mới thấy. Chạy local (JOB_RUNNER=thread) thì hai bên dùng chung
đĩa nên các hàm này không làm gì cả.
"""
from __future__ import annotations

import logging

from config.settings import JOB_RUNNER, MODAL_DATA_VOLUME

logger = logging.getLogger(__name__)


def _volume():
    import modal

    return modal.Volume.from_name(MODAL_DATA_VOLUME)


def commit_volume() -> None:
    """Ghi thay đổi trên volume xuống ngay, không đợi commit nền.

    Modal tự commit vài giây một lần, nhưng có hai lúc không chờ được:
    job được spawn ngay sau khi lưu video (container GPU có thể khởi động
    trước và không thấy file), và khi xoá file thì người dùng cần thấy kết
    quả ngay.
    """
    if JOB_RUNNER != "modal":
        return
    try:
        _volume().commit()
    except Exception:
        logger.exception("Không commit được volume")


#: Tên cũ, giữ lại cho chỗ gọi sau khi lưu upload.
commit_uploads = commit_volume


def refresh_outputs() -> None:
    """Nạp lại volume để thấy file mà container GPU vừa ghi."""
    if JOB_RUNNER != "modal":
        return
    try:
        _volume().reload()
    except Exception:
        logger.exception("Không reload được volume khi phục vụ file")
