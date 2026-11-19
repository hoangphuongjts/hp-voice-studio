"""Test routes TK2 qua TestClient + FakeEngine (T3.2/T3.3/T3.4/T3.5 phần API).

Routes lấy engine qua app.state.engine (quy ước DI — xem hpvoice/api/helpers.py);
test gắn FakeEngine nên kết quả là WAV tổng hợp, KHÔNG phải giọng thật.
"""

import io
import json
import zipfile

import fitz  # PyMuPDF
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hpvoice.api import routes_batch, routes_dialogue, routes_files, routes_srt
from hpvoice.engines.fake import FakeEngine

SRT_BYTES = b"""1
00:00:00,000 --> 00:00:02,000
Xin chao cac ban!

2
00:00:02,500 --> 00:00:05,000
Tam biet nhe!
"""

VTT_BYTES = b"""WEBVTT

00:00.000 --> 00:02.000
Xin chao cac ban!
"""


@pytest.fixture()
def client():
    app = FastAPI()
    app.state.engine = FakeEngine()
    app.include_router(routes_dialogue.router)
    app.include_router(routes_batch.router)
    app.include_router(routes_srt.router)
    app.include_router(routes_files.router)
    return TestClient(app)


def test_conversation_route(client):
    resp = client.post("/api/tts/conversation", json={
        "lines": [
            {"speaker": "An", "text": "Xin chào các bạn!"},
            {"speaker": "Bình", "text": "Chào An nhé!"},
            {"speaker": "An", "text": "Khỏe không bạn?"},
        ],
        "speakers": {"An": "Trúc Ly", "Bình": "Hải Đăng"},
    })
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("audio/wav")
    assert len(resp.content) > 1000
    from urllib.parse import unquote

    speakers = unquote(resp.headers["X-Speakers"])
    assert "An=Trúc Ly" in speakers
    assert "Bình=Hải Đăng" in speakers


def test_conversation_route_unknown_speaker_400(client):
    resp = client.post("/api/tts/conversation", json={
        "lines": [{"speaker": "Lạ", "text": "Xin chào!"}],
        "speakers": {"An": "Trúc Ly"},
    })
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "bad_request"


def test_batch_route_json_zip(client):
    resp = client.post("/api/tts/batch", json={
        "items": [
            {"id": "P1", "text": "Xin chào!"},
            {"id": "P2", "text": ""},  # mục lỗi: không chết batch
            {"id": "P3", "text": "Tạm biệt!"},
        ]
    })
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        names = zf.namelist()
        manifest = json.loads(zf.read([n for n in names if n.endswith("manifest.json")][0]))
    assert len([n for n in names if n.endswith(".wav")]) == 2
    statuses = {i["id"]: i["status"] for i in manifest["items"]}
    assert statuses == {"P1": "done", "P2": "error", "P3": "done"}


def test_batch_route_upload_txt(client):
    resp = client.post(
        "/api/tts/batch/upload",
        files={"file": ("danh-sach.txt", b"[P1] Xin chao\n[P2] Tam biet\n")},
    )
    assert resp.status_code == 200, resp.text
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        names = zf.namelist()
    assert len([n for n in names if n.endswith(".wav")]) == 2


def test_batch_route_too_many_items_400(client):
    resp = client.post("/api/tts/batch", json={
        "items": [{"id": f"P{i}", "text": "x"} for i in range(501)]
    })
    assert resp.status_code == 400


def test_srt_dub_route_srt(client):
    resp = client.post(
        "/api/tts/srt-dub",
        files={"file": ("phu-de.srt", SRT_BYTES)},
        data={"voice_id": "Hải Đăng", "speed": "1.0"},
    )
    assert resp.status_code == 200, resp.text
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        names = zf.namelist()
        report = json.loads(zf.read("report.json"))
        srt_out = zf.read("dub.srt").decode("utf-8")
    assert "dub.wav" in names and "dub.srt" in names and "report.json" in names
    assert report["cues"] == 2
    assert report["delayed"] == []
    assert "Xin chao cac ban!" in srt_out


def test_srt_dub_route_vtt(client):
    resp = client.post(
        "/api/tts/srt-dub",
        files={"file": ("phu-de.vtt", VTT_BYTES)},
        data={"voice_id": "Hải Đăng"},
    )
    assert resp.status_code == 200, resp.text
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        report = json.loads(zf.read("report.json"))
    assert report["cues"] == 1


def test_srt_dub_route_bad_file_400(client):
    resp = client.post(
        "/api/tts/srt-dub",
        files={"file": ("x.txt", b"khong phai srt")},
        data={"voice_id": "Hải Đăng"},
    )
    assert resp.status_code == 400


def test_files_read_txt_route(client):
    resp = client.post(
        "/api/files/read",
        files={"file": ("ghi-chu.txt", "Xin   chào\ncác bạn!".encode("utf-8"))},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["text"] == "Xin chào\ncác bạn!"
    assert data["kind"] == "txt"
    assert "bản quyền" in data["copyright_note"]


def test_files_read_pdf_route(client):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Noi dung PDF mau.", fontsize=12)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    resp = client.post(
        "/api/files/read",
        files={"file": ("mau.pdf", buf.getvalue())},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["kind"] == "pdf"
    assert "Noi dung PDF mau" in data["text"]


def test_files_read_scanned_pdf_400(client):
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100))
    page.insert_image(fitz.Rect(72, 72, 172, 172), pixmap=pix)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    resp = client.post(
        "/api/files/read",
        files={"file": ("scan.pdf", buf.getvalue())},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "scanned_pdf_no_ocr"
    assert "v1 không OCR" in resp.json()["error"]["message"]
