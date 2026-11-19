"""Test đường dẫn Unicode + khoảng trắng (TK4.7, SPEC §12/§10 T4.5, TH-32/C21).

Thư mục "Thư mục có dấu tiếng Việt" chứa config, history, preview cache,
file WAV — chạy ConfigStore + HistoryStore + PreviewCache + ghi/đọc WAV
thật trên VM Linux. Đường dẫn Windows C:\\Người dùng\\HP Voice Studio vẫn
chờ kiểm chứng thật trên máy Windows (C21) — test này chỉ chứng minh các
thành phần Python xử lý đúng Unicode, không chứng minh được máy Windows.
"""
from __future__ import annotations

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from hpvoice.api.server import create_app
from hpvoice.config import ConfigStore
from hpvoice.engines.fake import fake_wav_bytes
from hpvoice.jobs.history import HistoryStore, PreviewCache

UNICODE_DIRNAME = "Thư mục có dấu tiếng Việt"


def _unicode_base(tmp_path):
    base = tmp_path / UNICODE_DIRNAME / "HP Voice Studio"
    base.mkdir(parents=True)
    return base


def test_configstore_doc_ghi_unicode_path(tmp_path):
    """ConfigStore đọc/ghi config.yaml trong thư mục có dấu + khoảng trắng."""
    base = _unicode_base(tmp_path)
    config_path = base / "config.yaml"
    store = ConfigStore(path=config_path)
    store.update({
        "storage": {
            "output_dir": str(base / "đầu ra"),
            "history_dir": str(base / "lịch sử"),
        },
    })
    assert config_path.is_file()
    reloaded = ConfigStore(path=config_path)
    assert reloaded.get("storage.output_dir") == str(base / "đầu ra")
    assert reloaded.get("storage.history_dir") == str(base / "lịch sử")


def test_historystore_ghi_doc_trong_thu_muc_co_dau(tmp_path):
    """HistoryStore.add + list_items trong thư mục lịch sử có dấu."""
    base = _unicode_base(tmp_path)
    history_dir = base / "lịch sử đã tạo"
    store = HistoryStore(history_dir=history_dir, max_history_gb=5)
    wav = fake_wav_bytes("Xin chào, đây là bản kiểm thử đường dẫn Unicode.")
    item = store.add(
        text_preview="Xin chào, đây là bản kiểm thử đường dẫn Unicode.",
        voice_id="Hải Đăng", engine="v3", duration_sec=1.0, audio_bytes=wav,
        srt_text="1\n00:00:00,000 --> 00:00:01,000\nXin chào\n",
    )
    assert item["id"]
    assert (history_dir / item["audio_path"]).is_file()
    assert (history_dir / item["srt_path"]).is_file()
    items, total = store.list_items(limit=10)
    assert total == 1
    assert items[0]["text_preview"].startswith("Xin chào")
    # Nạp lại từ đĩa (index JSON có dấu) vẫn đọc được.
    reloaded = HistoryStore(history_dir=history_dir, max_history_gb=5)
    assert reloaded.get(item["id"]) is not None


def test_previewcache_trong_thu_muc_co_dau(tmp_path):
    """PreviewCache.put/get trong thư mục cache có dấu."""
    base = _unicode_base(tmp_path)
    cache = PreviewCache(cache_dir=base / "bộ nhớ đệm")
    data = fake_wav_bytes("nghe thử giọng")
    path = cache.put("giong-Hải Đăng-nghe-thử", data)
    assert path.is_file()
    assert cache.get("giong-Hải Đăng-nghe-thu") is None  # key khác -> miss
    assert cache.get("giong-Hải Đăng-nghe-thử") == data


def test_ghi_doc_wav_trong_thu_muc_co_dau(tmp_path):
    """Ghi WAV bằng soundfile vào thư mục có dấu rồi đọc lại đúng mẫu."""
    base = _unicode_base(tmp_path)
    wav_path = base / "đầu ra" / "bản đọc thử.wav"
    wav_path.parent.mkdir(parents=True)
    sr = 48000
    t = np.arange(int(0.5 * sr), dtype=np.float32) / sr
    samples = (0.3 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)
    sf.write(str(wav_path), samples, sr)
    assert wav_path.is_file() and wav_path.stat().st_size > 0
    data, sr_read = sf.read(str(wav_path))
    assert sr_read == 48000
    assert len(data) == len(samples)
    assert abs(float(np.max(np.abs(data))) - 0.3) < 0.01


def test_server_chay_voi_data_dir_co_dau(tmp_path, fake_engine):
    """create_app với data_dir có dấu: /health 200, /v1/voices liệt kê được."""
    base = _unicode_base(tmp_path)
    config = ConfigStore(path=base / "config.yaml")
    app = create_app(engine=fake_engine, config=config, data_dir=base / "dữ liệu")
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        voices = client.get("/v1/voices")
        assert voices.status_code == 200
    assert (base / "dữ liệu" / "history").is_dir()
    assert (base / "dữ liệu" / "outputs").is_dir()
