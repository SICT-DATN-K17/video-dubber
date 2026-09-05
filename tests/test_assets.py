"""Canh hai thứ im lặng hỏng: icon thiếu tên, và CSS quên build lại.

Cả hai đều không làm test nào khác đỏ — trang vẫn trả 200, chỉ là người dùng
nhìn thấy chữ "account_circle" thay cho icon, hoặc một trang không có định dạng.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
BUILT_CSS = ROOT / "static" / "css" / "app.css"

#: <span class="material-symbols-outlined ...">ten_icon</span>
ICON_IN_TEMPLATE = re.compile(r"material-symbols-outlined[^<>]*>\s*([a-z_0-9]+)")


def icons_used() -> set[str]:
    return {
        name
        for path in TEMPLATES.rglob("*.html")
        for name in ICON_IN_TEMPLATE.findall(path.read_text(encoding="utf-8"))
    }


def icons_requested() -> set[str]:
    head = (TEMPLATES / "_head.html").read_text(encoding="utf-8")
    match = re.search(r"icon_names=([a-z_0-9,]+)", head)
    assert match, "_head.html phải lọc icon bằng icon_names, không tải cả bộ font"
    return set(match.group(1).split(","))


def test_every_icon_used_is_requested():
    """Thiếu tên trong icon_names thì icon hiện ra thành chữ, không ai báo lỗi."""
    missing = icons_used() - icons_requested()
    assert not missing, (
        "Icon dùng trong template nhưng chưa khai trong icon_names của _head.html: "
        + ", ".join(sorted(missing))
    )


def test_no_unused_icons_requested():
    """Icon thừa thì font phình ra mà không ai dùng."""
    unused = icons_requested() - icons_used()
    assert not unused, "icon_names khai thừa: " + ", ".join(sorted(unused))


def test_icon_font_is_subset_not_whole_family():
    head = (TEMPLATES / "_head.html").read_text(encoding="utf-8")
    # Bo font day du nang 1,13 MB; ban loc 32 icon nang khoang 5,8 KB.
    assert "wght,FILL@100..700,0..1" not in head
    assert "icon_names=" in head


# ── CSS đã build ─────────────────────────────────────────────
def test_built_css_exists_and_is_committed():
    """Image Modal không có Node, nó chỉ chép file đã build vào."""
    assert BUILT_CSS.exists(), "Thiếu static/css/app.css — chạy `npm run build:css`"
    assert BUILT_CSS.stat().st_size > 5_000


def test_pages_link_built_css_not_the_play_cdn(client):
    """Kiểm tra HTML đã render, không phải mã nguồn: chú thích Jinja bị bỏ đi
    lúc render, nên soi file gốc sẽ khớp nhầm vào chính lời giải thích."""
    html = client.get("/login").get_data(as_text=True)
    assert "cdn.tailwindcss.com" not in html, "Bản CDN chỉ để thử nghiệm, không dùng cho production"
    assert "/static/css/app.css" in html


def test_built_css_covers_classes_the_templates_use():
    """Tailwind chỉ giữ class nó quét thấy — class dựng bằng JS dễ bị loại nhầm."""
    css = BUILT_CSS.read_text(encoding="utf-8")
    for cls in ["bg-surface-container", "text-on-surface-variant", "font-headline-xl",
                "bg-error", "bg-tertiary", "text-primary", "-translate-x-full"]:
        assert cls in css, f"Class {cls} không có trong CSS đã build"


@pytest.mark.skipif(not (ROOT / "node_modules").exists(), reason="chưa chạy npm install")
def test_built_css_is_up_to_date():
    """Sửa template rồi quên build lại thì trang mất định dạng ở production."""
    before = BUILT_CSS.read_bytes()
    subprocess.run(
        ["npm", "run", "build:css"], cwd=ROOT, check=True,
        capture_output=True, shell=sys.platform == "win32",
    )
    assert BUILT_CSS.read_bytes() == before, (
        "static/css/app.css cũ hơn template — chạy `npm run build:css` rồi commit lại"
    )
