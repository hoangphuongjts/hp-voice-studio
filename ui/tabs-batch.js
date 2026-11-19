/* HP Voice Studio — Tab Tạo hàng loạt (TK3.4, test T3.5, SPEC §5 + TH-16/TH-28).
 *
 * - Nhập trực tiếp (mốc [P1], [P2]…) hoặc tải file .txt/.json (POST /api/tts/batch
 *   JSON, POST /api/tts/batch/upload multipart).
 * - Mỗi mốc 1 file; tải từng file / tải tất cả (.zip); tiến trình từng mục;
 *   mục lỗi thử lại riêng (chỉ gửi lại các mục lỗi, không chạy lại cả batch).
 * - Danh sách mục render bằng VirtualList (TK3.7) để batch 100–500 mục không lag.
 * - Nghe thử từng mục qua player dùng chung (không tạo Audio riêng).
 */
(function () {
  'use strict';

  var NS = window.HPVoiceStudio = window.HPVoiceStudio || {};
  var API_BASE = 'http://127.0.0.1:8124';
  var MAX_ITEMS = 500;

  function api() { return NS.api || null; }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function hpFetch(path, opts) {
    if (api() && typeof api().fetchJson === 'function') { return api().fetchJson(path, opts); }
    if (api() && typeof api().request === 'function') { return api().request(path, opts); }
    return fetch(API_BASE + path, opts);
  }

  function registerTab(def) {
    if (typeof NS.registerTab === 'function') { NS.registerTab(def); return; }
    (NS._pendingTabs = NS._pendingTabs || []).push(def);
  }

  /** Parse text có mốc [P1], [P2]… thành danh sách {id, text}. */
  function parseMarkers(text) {
    var items = [];
    var current = null;
    String(text || '').split('\n').forEach(function (line) {
      var m = line.match(/^\s*\[(P\d+)\]\s*(.*)$/);
      if (m) {
        if (current) { items.push(current); }
        current = { id: m[1], text: (m[2] || '').trim() };
      } else if (current) {
        current.text = (current.text + ' ' + line.trim()).trim();
      }
    });
    if (current) { items.push(current); }
    return items;
  }

  function render(el) {
    el.innerHTML =
      '<h2>Tạo hàng loạt</h2>'
      + '<p class="hp-hint">Mỗi mốc 1 file (tối đa ' + MAX_ITEMS + ' mục/lần). Mục lỗi không làm chết cả batch — '
      + 'thử lại riêng từng mục. Danh sách dùng virtual list nên 100–500 mục vẫn không lag.</p>'
      + '<div class="hp-row"><label>Giọng cho cả batch <select id="batch-voice"></select></label></div>'
      + '<textarea id="batch-input" rows="8" placeholder="[P1] Câu đầu tiên cần đọc.\n[P2] Câu thứ hai cần đọc.\n…"></textarea>'
      + '<div class="hp-row"><button id="batch-run" type="button">Tạo hàng loạt</button>'
      + '<label class="hp-file-label">…hoặc tải file .txt/.json '
      + '<input id="batch-file" type="file" accept=".txt,.json"></label>'
      + '<button id="batch-download-all" type="button" disabled>Tải tất cả (.zip)</button></div>'
      + '<p id="batch-status" role="status"></p>'
      + '<h3>Tiến trình từng mục</h3>'
      + '<div id="batch-list" style="height:320px;border:1px solid #ccc;"><p>Chưa có mục nào.</p></div>';

    var inputEl = el.querySelector('#batch-input');
    var statusEl = el.querySelector('#batch-status');
    var listEl = el.querySelector('#batch-list');
    var runBtn = el.querySelector('#batch-run');
    var zipBtn = el.querySelector('#batch-download-all');

    var items = [];   // {id, text, voice_id, status: pending|running|done|error, error, blobUrl}
    var zipBlob = null;
    var zipEntries = null; // {tenFile: ArrayBuffer} đọc từ ZIP trả về
    var vlist = null;

    function setStatus(msg, isErr) {
      statusEl.textContent = msg || '';
      statusEl.style.color = isErr ? '#b00020' : '';
    }

    function rowHtml(it) {
      var badge = { pending: 'Chờ', running: '… Đang tạo', done: '✓ Xong', error: '✗ Lỗi' }[it.status] || it.status;
      var extra = '';
      if (it.status === 'error') {
        extra = ' <span title="' + esc(it.error || '') + '">' + esc(it.error || 'Lỗi') + '</span>'
          + ' <button type="button" data-retry="' + esc(it.id) + '">Thử lại riêng</button>';
      }
      if (it.status === 'done' && it.blobUrl) {
        extra = ' <button type="button" data-play="' + esc(it.id) + '">Nghe</button>'
          + ' <button type="button" data-dl="' + esc(it.id) + '">Tải file</button>';
      }
      return '<strong>' + esc(it.id) + '</strong> — ' + esc(it.text.slice(0, 80))
        + (it.text.length > 80 ? '…' : '') + ' — ' + badge + extra;
    }

    function ensureList() {
      if (vlist) { vlist.setItems(items); return; }
      if (typeof NS.VirtualList === 'function') {
        listEl.innerHTML = '';
        vlist = new NS.VirtualList(listEl, {
          itemHeight: 44, items: items, overscan: 5,
          renderItem: function (it) { return rowHtml(it); }
        });
      } else {
        // Dự phòng khi virtual-list.js chưa nạp: render thường (chỉ dùng tạm).
        listEl.innerHTML = items.map(rowHtml).join('');
      }
      bindRowButtons();
    }

    function refreshList() {
      if (vlist) { vlist.setItems(items); }
      else { listEl.innerHTML = items.map(rowHtml).join(''); }
      bindRowButtons();
    }

    function bindRowButtons() {
      Array.prototype.forEach.call(listEl.querySelectorAll('[data-retry]'), function (btn) {
        btn.addEventListener('click', function () { retryOne(btn.getAttribute('data-retry')); });
      });
      Array.prototype.forEach.call(listEl.querySelectorAll('[data-play]'), function (btn) {
        btn.addEventListener('click', function () {
          var it = items.find(function (x) { return x.id === btn.getAttribute('data-play'); });
          if (it && it.blobUrl && NS.player) { NS.player.play(it.blobUrl, 'Batch ' + it.id); }
        });
      });
      Array.prototype.forEach.call(listEl.querySelectorAll('[data-dl]'), function (btn) {
        btn.addEventListener('click', function () {
          var it = items.find(function (x) { return x.id === btn.getAttribute('data-dl'); });
          if (it && it.blobUrl) {
            var a = document.createElement('a');
            a.href = it.blobUrl; a.download = it.id + '.wav'; a.click();
          }
        });
      });
    }

    function applyZipEntries(entries) {
      // ZIP server trả: <batch>-<id>.wav + <batch>-manifest.json.
      zipEntries = entries;
      var manifest = null;
      Object.keys(entries).forEach(function (name) {
        if (/manifest\.json$/i.test(name)) {
          try { manifest = JSON.parse(new TextDecoder().decode(entries[name])); } catch (e) { /* bỏ qua */ }
        }
      });
      items.forEach(function (it) {
        var wavName = Object.keys(entries).find(function (n) { return n.indexOf('-' + it.id + '.wav') >= 0; });
        var m = manifest && manifest.items ? manifest.items.find(function (x) { return x.id === it.id; }) : null;
        if (wavName) {
          it.status = 'done';
          if (it.blobUrl) { URL.revokeObjectURL(it.blobUrl); }
          it.blobUrl = URL.createObjectURL(new Blob([entries[wavName]], { type: 'audio/wav' }));
          it.error = '';
        } else if (m && m.status === 'error') {
          it.status = 'error';
          it.error = m.error || 'Lỗi không rõ.';
        } else if (m && m.status === 'done') {
          it.status = 'done';
        } else {
          it.status = 'error';
          it.error = 'Không có file trong ZIP trả về.';
        }
      });
      var done = items.filter(function (x) { return x.status === 'done'; }).length;
      var failed = items.filter(function (x) { return x.status === 'error'; }).length;
      setStatus('Xong: ' + done + '/' + items.length + ' mục'
        + (failed ? ' — ' + failed + ' mục lỗi, bấm "Thử lại riêng" ở từng mục.' : '.')
        + ' Bấm "Tải tất cả (.zip)" để lấy toàn bộ file.');
      refreshList();
    }

    function runBatch(batchItems) {
      var voice = el.querySelector('#batch-voice').value || '';
      items = batchItems.map(function (it) {
        return { id: it.id, text: it.text, voice_id: voice, status: 'running', error: '', blobUrl: null };
      });
      ensureList();
      setStatus('Đang tạo ' + items.length + ' mục… (POST /api/tts/batch)');
      hpFetch('/api/tts/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: items.map(function (it) { return { id: it.id, text: it.text, voice_id: it.voice_id }; }),
          format: 'wav'
        })
      }).then(function (resp) {
        if (!resp.ok) { return resp.text().then(function (t) { throw new Error('API trả ' + resp.status + ': ' + t); }); }
        return resp.blob();
      }).then(function (blob) {
        zipBlob = blob;
        zipBtn.disabled = false;
        if (typeof NS.readZip === 'function') {
          return NS.readZip(blob).then(applyZipEntries);
        }
        items.forEach(function (it) { it.status = 'done'; });
        setStatus('Đã tạo xong (không đọc được manifest trong ZIP — tải ZIP về để xem từng file).');
        refreshList();
      }).catch(function (e) {
        items.forEach(function (it) { if (it.status === 'running') { it.status = 'error'; it.error = e.message; } });
        setStatus('Không tạo được batch: ' + e.message, true);
        refreshList();
      });
    }

    function retryOne(id) {
      var it = items.find(function (x) { return x.id === id; });
      if (!it) { return; }
      it.status = 'running'; it.error = '';
      refreshList();
      setStatus('Đang thử lại riêng mục ' + id + '… (POST /api/tts/batch, chỉ 1 mục)');
      hpFetch('/api/tts/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: [{ id: it.id, text: it.text, voice_id: it.voice_id }], format: 'wav' })
      }).then(function (resp) {
        if (!resp.ok) { return resp.text().then(function (t) { throw new Error('API trả ' + resp.status + ': ' + t); }); }
        return resp.blob();
      }).then(function (blob) {
        if (typeof NS.readZip === 'function') {
          return NS.readZip(blob).then(function (entries) {
            var wavName = Object.keys(entries).find(function (n) { return n.indexOf('-' + it.id + '.wav') >= 0; });
            if (wavName) {
              it.status = 'done';
              if (it.blobUrl) { URL.revokeObjectURL(it.blobUrl); }
              it.blobUrl = URL.createObjectURL(new Blob([entries[wavName]], { type: 'audio/wav' }));
              setStatus('Mục ' + id + ' đã tạo lại xong.');
            } else {
              it.status = 'error';
              it.error = 'Không có file trong ZIP trả về.';
              setStatus('Mục ' + id + ' vẫn lỗi: không có file trong ZIP trả về.', true);
            }
            refreshList();
          });
        }
        it.status = 'done';
        setStatus('Mục ' + id + ' đã tạo lại xong (không đọc được manifest).');
        refreshList();
      }).catch(function (e) {
        it.status = 'error';
        it.error = e.message;
        setStatus('Thử lại mục ' + id + ' vẫn lỗi: ' + e.message, true);
        refreshList();
      });
    }

    runBtn.addEventListener('click', function () {
      var parsed = parseMarkers(inputEl.value);
      if (!parsed.length) {
        setStatus('Chưa có mục nào. Nhập theo mẫu [P1] câu cần đọc, mỗi mốc 1 dòng.', true);
        return;
      }
      if (parsed.length > MAX_ITEMS) {
        setStatus('Batch tối đa ' + MAX_ITEMS + ' mục/lần, đã nhập ' + parsed.length + ' mục.', true);
        return;
      }
      runBatch(parsed);
    });

    el.querySelector('#batch-file').addEventListener('change', function (e) {
      var file = e.target.files && e.target.files[0];
      if (!file) { return; }
      if (!/\.(txt|json)$/i.test(file.name)) {
        setStatus('Chỉ nhận file .txt/.json cho batch.', true); return;
      }
      setStatus('Đang tạo batch từ file "' + file.name + '"… (POST /api/tts/batch/upload)');
      var form = new FormData();
      form.append('file', file);
      items = [];
      hpFetch('/api/tts/batch/upload', { method: 'POST', body: form })
        .then(function (resp) {
          if (!resp.ok) { return resp.text().then(function (t) { throw new Error('API trả ' + resp.status + ': ' + t); }); }
          return resp.blob();
        })
        .then(function (blob) {
          zipBlob = blob;
          zipBtn.disabled = false;
          if (typeof NS.readZip === 'function') {
            return NS.readZip(blob).then(function (entries) {
              var manifest = null;
              var manifestName = Object.keys(entries).find(function (n) { return /manifest\.json$/i.test(n); });
              if (manifestName) {
                try { manifest = JSON.parse(new TextDecoder().decode(entries[manifestName])); } catch (err) { /* bỏ qua */ }
              }
              if (manifest && manifest.items) {
                items = manifest.items.map(function (m) {
                  return { id: m.id, text: '', voice_id: '', status: m.status === 'done' ? 'done' : 'error', error: m.error || '', blobUrl: null };
                });
                items.forEach(function (it) {
                  var wavName = Object.keys(entries).find(function (n) { return n.indexOf('-' + it.id + '.wav') >= 0; });
                  if (wavName && it.status === 'done') {
                    it.blobUrl = URL.createObjectURL(new Blob([entries[wavName]], { type: 'audio/wav' }));
                  }
                });
                var done = items.filter(function (x) { return x.status === 'done'; }).length;
                setStatus('Xong: ' + done + '/' + items.length + ' mục từ file "' + file.name + '".');
              } else {
                setStatus('Đã tạo xong từ file "' + file.name + '" — tải ZIP về để xem từng file (không đọc được manifest).');
              }
              ensureList();
            });
          }
          setStatus('Đã tạo xong từ file "' + file.name + '" — tải ZIP về để xem từng file.');
        })
        .catch(function (e) { setStatus('Không tạo được batch từ file: ' + e.message, true); });
      e.target.value = '';
    });

    zipBtn.addEventListener('click', function () {
      if (!zipBlob) { return; }
      var url = URL.createObjectURL(zipBlob);
      var a = document.createElement('a');
      a.href = url; a.download = 'batch.zip'; a.click();
      setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
    });

    // Nạp danh sách giọng.
    hpFetch('/voices?engine=v3').then(function (resp) { return resp.ok ? resp.json() : []; })
      .then(function (list) {
        var sel = el.querySelector('#batch-voice');
        sel.innerHTML = '<option value="">Giọng mặc định</option>'
          + (Array.isArray(list) ? list : []).map(function (v) {
            return '<option value="' + esc(v.id) + '">' + esc(v.name || v.id) + '</option>';
          }).join('');
      }).catch(function () { /* để trống, server dùng giọng mặc định */ });
  }

  NS.parseBatchMarkers = parseMarkers;

  registerTab({ id: 'batch', group: 'Tạo', label: 'Tạo hàng loạt', render: render });
})();
