"""copy vs mã hoá lại theo codec nguồn — xem core/video_composer.py.

Bug thật gặp trên production: video nguồn là AV1 (phổ biến với video tải mới
từ YouTube gần đây), "-c:v copy" chép nguyên codec đó sang, job báo "Hoàn
tất" nhưng người dùng bấm không xem được — nhiều trình duyệt/điện thoại
không giải mã được AV1. Test này không dựng ffmpeg thật (không cần video mẫu
thật để tái tạo mọi codec), mà bắt đúng LỆNH ffmpeg được gọi để xác nhận
đúng nhánh (-c:v copy vs -c:v libx264) được chọn theo codec dò được.
"""
from __future__ import annotations

import core.video_composer as vc_mod
from core.transcriber import Segment
from core.video_composer import VideoComposer


class FakeCompleted:
    def __init__(self, stdout: str = ""):
        self.stdout = stdout


def _prepare_files(tmp_path):
    video = tmp_path / "in.mp4"
    video.write_bytes(b"fake")
    tts = tmp_path / "seg0.wav"
    tts.write_bytes(b"fake")
    return video, tts


def _fake_run_command(probe_stdout=None, probe_raises=False):
    """Giả lập run_command: phân biệt lệnh ffprobe (dò codec) với lệnh ffmpeg
    (ghép video thật) qua cmd[0], vì compose() gọi cả hai."""
    calls = []

    def fake(cmd, **kwargs):
        calls.append(cmd)
        if cmd[0] == "ffprobe":
            if probe_raises:
                raise RuntimeError("Không đọc được codec video nguồn.")
            return FakeCompleted(stdout=probe_stdout or "")
        return FakeCompleted(stdout="")

    return fake, calls


def _ffmpeg_cmd(calls):
    ffmpeg_calls = [c for c in calls if c[0] == "ffmpeg"]
    assert len(ffmpeg_calls) == 1, "compose() phải gọi ffmpeg đúng một lần"
    return ffmpeg_calls[0]


def _flag_value(cmd, flag):
    return cmd[cmd.index(flag) + 1]


# ── Nguồn đã là H.264 ─────────────────────────────────────────
def test_h264_source_keeps_fast_copy(tmp_path, monkeypatch):
    video, tts = _prepare_files(tmp_path)
    fake, calls = _fake_run_command(probe_stdout="h264\n")
    monkeypatch.setattr(vc_mod, "run_command", fake)
    monkeypatch.setattr(vc_mod, "OUTPUT_DIR", tmp_path)

    VideoComposer().compose(video, [Segment(0, 1, "hi")], [tts])

    assert _flag_value(_ffmpeg_cmd(calls), "-c:v") == "copy"


# ── Nguồn không phải H.264 — đúng bug thật gặp phải ────────────
def test_non_h264_source_gets_reencoded_to_h264(tmp_path, monkeypatch):
    video, tts = _prepare_files(tmp_path)
    fake, calls = _fake_run_command(probe_stdout="av1\n")
    monkeypatch.setattr(vc_mod, "run_command", fake)
    monkeypatch.setattr(vc_mod, "OUTPUT_DIR", tmp_path)

    VideoComposer().compose(video, [Segment(0, 1, "hi")], [tts])

    cmd = _ffmpeg_cmd(calls)
    assert _flag_value(cmd, "-c:v") == "libx264"
    # 10-bit hay chroma khac 4:2:0 cũng là một nguồn không tương thích khác —
    # ép về yuv420p cho chắc, không chỉ đổi tên codec.
    assert _flag_value(cmd, "-pix_fmt") == "yuv420p"


# ── Không dò được codec (ffprobe lỗi) ──────────────────────────
def test_codec_detection_failure_defaults_to_reencode(tmp_path, monkeypatch):
    """Không đọc được codec thì phải coi là KHÔNG an toàn — mã hoá lại cho
    chắc, đừng liều dùng copy chỉ vì không biết chắc nguồn là gì."""
    video, tts = _prepare_files(tmp_path)
    fake, calls = _fake_run_command(probe_raises=True)
    monkeypatch.setattr(vc_mod, "run_command", fake)
    monkeypatch.setattr(vc_mod, "OUTPUT_DIR", tmp_path)

    VideoComposer().compose(video, [Segment(0, 1, "hi")], [tts])

    assert _flag_value(_ffmpeg_cmd(calls), "-c:v") == "libx264"


def test_codec_names_compared_case_insensitively(tmp_path, monkeypatch):
    video, tts = _prepare_files(tmp_path)
    fake, calls = _fake_run_command(probe_stdout="H264\n")  # ffprobe hiếm khi viết hoa, nhưng đừng phụ thuộc vào đó
    monkeypatch.setattr(vc_mod, "run_command", fake)
    monkeypatch.setattr(vc_mod, "OUTPUT_DIR", tmp_path)

    VideoComposer().compose(video, [Segment(0, 1, "hi")], [tts])

    assert _flag_value(_ffmpeg_cmd(calls), "-c:v") == "copy"
