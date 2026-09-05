"""Khung giao diện dùng chung: menu điện thoại, hạn mức, trang lỗi."""
from __future__ import annotations


# ── Menu trên điện thoại ─────────────────────────────────────
def test_sidebar_has_mobile_toggle(as_user):
    """Dưới 1024px thanh bên trượt ra ngoài, phải có nút kéo nó vào."""
    html = as_user.get("/").get_data(as_text=True)
    assert 'id="navToggle"' in html
    assert 'aria-controls="sidebar"' in html
    assert "-translate-x-full lg:translate-x-0" in html


def test_sidebar_is_not_hidden_outright(as_user):
    """Bản cũ dùng 'hidden lg:flex' nên trên điện thoại không có cách nào mở."""
    html = as_user.get("/").get_data(as_text=True)
    assert 'id="sidebar"' in html
    assert "hidden lg:flex" not in html


# ── Hạn mức hiển thị cho người dùng ──────────────────────────
def test_user_sees_quota_badge(as_user):
    html = as_user.get("/").get_data(as_text=True)
    assert 'id="quotaBadge"' in html
    assert "/api/usage" in html


def test_admin_sees_unlimited_instead_of_badge(as_admin):
    """Admin được miễn hạn mức nên thanh tiến độ vô nghĩa."""
    html = as_admin.get("/").get_data(as_text=True)
    assert 'id="quotaBadge"' not in html
    assert "không giới hạn" in html


# ── Trang lỗi ────────────────────────────────────────────────
def test_404_uses_our_template_not_werkzeug_default(as_user):
    response = as_user.get("/khong-co-trang-nay")
    html = response.get_data(as_text=True)
    assert response.status_code == 404
    assert "Không tìm thấy trang" in html
    assert "DUB_STUDIO" in html
    assert "The requested URL was not found" not in html


def test_403_page_is_styled_and_in_vietnamese(as_user):
    response = as_user.get("/quan-tri/thong-ke")
    html = response.get_data(as_text=True)
    assert response.status_code == 403
    assert "Không có quyền truy cập" in html
    assert "DUB_STUDIO" in html


def test_error_page_offers_login_when_signed_out(client):
    response = client.get("/khong-co-trang-nay")
    assert response.status_code == 404
    assert "/login" in response.get_data(as_text=True)


def test_api_errors_stay_json(as_user):
    """Trang lỗi HTML không được lấn sang /api/*."""
    response = as_user.get("/api/admin/stats")
    assert response.status_code == 403
    assert response.is_json


def test_english_werkzeug_description_is_not_shown(as_user):
    """abort(404) không kèm mô tả riêng thì không hiện câu tiếng Anh mặc định."""
    html = as_user.get("/khong-co-trang-nay").get_data(as_text=True)
    assert "Not Found" not in html


# ── Khung xương lúc chờ dữ liệu ──────────────────────────────
# Ba trang admin nạp nội dung bằng fetch() sau khi trang đã hiện. Không có
# khung xương thì mạng chậm (đúng lúc người dùng thấy trang "load lâu") để lộ
# khoảng trắng vài giây trước khi bảng/biểu đồ hiện ra. Render sẵn trong HTML
# gốc — không đợi JS thêm vào — vì JS cũng phải tải xong mới chạy được.
def test_admin_stats_renders_skeleton_before_data_arrives(as_admin):
    html = as_admin.get("/quan-tri/thong-ke").get_data(as_text=True)
    assert 'data-skeleton="dailyChart"' in html
    assert 'data-skeleton="engineChart"' in html
    assert 'data-skeleton="stepChart"' in html
    assert html.count("animate-pulse") >= 3 + 3 + 5  # 3 hàng engineRows + 5 dòng topUsers


def test_admin_users_renders_skeleton_rows(as_admin):
    html = as_admin.get("/quan-tri/nguoi-dung").get_data(as_text=True)
    assert html.count("animate-pulse") >= 6  # 6 hàng khung xương trong <tbody>


def test_admin_system_renders_skeleton_cards(as_admin):
    html = as_admin.get("/quan-tri/he-thong").get_data(as_text=True)
    assert "animate-pulse" in html


def test_history_page_already_has_its_own_skeleton(as_user):
    """Mẫu animate-pulse này có từ trước — ba trang admin ở trên chỉ làm theo
    đúng kiểu đã có, không phải bịa ra một kiểu mới."""
    html = as_user.get("/lich-su").get_data(as_text=True)
    assert "animate-pulse" in html
