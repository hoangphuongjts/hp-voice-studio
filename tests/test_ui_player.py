"""Test TK3.7 — singleton player + virtual list (SPEC TH-28, test T3.5 phần UI).

- ui/player.js: toàn app chỉ có DUY NHẤT 1 lần ``new Audio`` (singleton);
  API phải có play/pause/stop, phát mới dừng phát cũ.
- ui/virtual-list.js: chỉ render hàng đang thấy trong viewport (tính từ
  scrollTop + clientHeight), dùng cho batch 100–500 mục + Bản đã tạo.
- Không tab nào của TK3 được tự tạo Audio riêng (grep toàn bộ ui/tabs-*.js).
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
UI = REPO / "ui"


def _read(name: str) -> str:
    return (UI / name).read_text(encoding="utf-8")


def test_player_single_audio_singleton():
    src = _read("player.js")
    # Chỉ đếm code thật: bỏ comment khối /* */ và comment dòng // trước khi đếm.
    code = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    code = re.sub(r"//.*", "", code)
    count = len(re.findall(r"new\s+Audio\s*\(", code))
    assert count == 1, f"player.js phải chứa đúng 1 lần 'new Audio' trong code, thấy {count} lần"
    assert "window.HPVoiceStudio.player" in src or "NS.player" in src
    # API bắt buộc: play / pause / stop (+ playBlob cho Blob WAV/MP3).
    for method in ("play:", "pause:", "stop:"):
        assert method in src, f"player.js thiếu phương thức {method}"
    # Phát mới dừng phát cũ (pause trước khi đổi src).
    assert "audio.pause()" in src
    # Không tạo Audio thứ hai qua document.createElement('audio').
    assert "createElement('audio')" not in src
    assert 'createElement("audio")' not in src


def test_no_tab_creates_its_own_audio():
    """Mọi tab nghe lại đều qua window.HPVoiceStudio.player, KHÔNG tạo Audio riêng."""
    for path in sorted(UI.glob("tabs-*.js")):
        src = path.read_text(encoding="utf-8")
        # Chỉ đếm code thật: bỏ comment khối /* */ và comment dòng // trước khi
        # kiểm tra (comment nhắc "KHÔNG tạo new Audio()" không phải code tạo Audio).
        code = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
        code = re.sub(r"//.*", "", code)
        assert "new Audio(" not in code, f"{path.name} tự tạo Audio riêng — phải dùng HPVoiceStudio.player"
        assert "createElement('audio')" not in code, f"{path.name} tự tạo thẻ audio"
        assert 'createElement("audio")' not in code, f"{path.name} tự tạo thẻ audio"


def test_virtual_list_renders_only_visible_rows():
    src = _read("virtual-list.js")
    assert "VirtualList" in src
    assert "window.HPVoiceStudio.VirtualList" in src or "NS.VirtualList" in src
    # Logic render theo viewport: vị trí cuộn + chiều cao khung nhìn.
    assert "scrollTop" in src, "thiếu tính toán từ scrollTop"
    assert "clientHeight" in src, "thiếu tính toán từ clientHeight"
    # Chỉ render khoảng đang thấy (+ đệm overscan), có spacer giữ chiều cao thật.
    assert "overscan" in src
    assert "visibleRange" in src or "start" in src
    assert "setItems" in src, "thiếu setItems để đổi dữ liệu"
    assert "addEventListener('scroll'" in src or 'addEventListener("scroll"' in src


def test_batch_and_history_use_virtual_list_and_player():
    for name in ("tabs-batch.js", "tabs-history.js"):
        src = _read(name)
        assert "VirtualList" in src, f"{name} chưa dùng VirtualList cho danh sách dài"
        assert "player" in src, f"{name} chưa dùng player dùng chung để nghe lại"
