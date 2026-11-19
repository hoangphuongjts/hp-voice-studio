/* HP Voice Studio — Tab Bản đã tạo (TK3.4, test T3.6, SPEC §5 + TH-16).
 *
 * - Danh sách bản đã tạo (tên, giọng, engine, thời lượng, dung lượng, ngày)
 *   từ GET /api/history — render bằng VirtualList (TK3.7).
 * - Nghe lại (qua player dùng chung), tải lại WAV/MP3/SRT, mở thư mục chứa
 *   file (bản web không mở được thư mục hệ thống: hiện đường dẫn + sao chép;
 *   bản desktop mở thư mục thật), xoá (DELETE /api/history/{id}).
 * - Hiển thị tổng dung lượng + chặn tạo mới khi vượt max_history_gb: khi API
 *   báo vượt (total_bytes >= max_history_gb) thì hiện cảnh báo đỏ rõ ràng
 *   + hướng dẫn xoá/xuất bớt để mở lại; việc chặn tạo mới do server thực thi
 *   (HistoryFullError), tab chỉ hiển thị cảnh báo.
 */
(function () {
  'use strict';

  var NS = window.HPVoiceStudio = window.HPVoiceStudio || {};
  var API_BASE = 'http://127.0.0.1:8124';

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

  function fmtBytes(n) {
    n = Number(n) || 0;
    if (n >= 1e9) { return (n / 1e9).toFixed(2) + ' GB'; }
    if (n >= 1e6) { return (n / 1e6).toFixed(1) + ' MB'; }
    if (n >= 1e3) { return (n / 1e3).toFixed(1) + ' KB'; }
    return n + ' B';
  }

  function fmtDate(s) {
    if (!s) { return 'không rõ'; }
    try { return new Date(s).toLocaleString('vi-VN'); } catch (e) { return String(s); }
  }

  function render(el) {
    el.innerHTML =
      '<h2>Bản đã tạo</h2>'
      + '<p id="history-total">Đang tải…</p>'
      + '<p id="history-warning" role="alert" style="display:none;color:#b00020;font-weight:bold;"></p>'
      + '<div class="hp-row"><button id="history-refresh" type="button">Tải lại</button></div>'
      + '<div id="history-list" style="height:360px;border:1px solid #ccc;"><p>Đang tải…</p></div>'
      + '<p id="history-status" role="status"></p>';

    var totalEl = el.querySelector('#history-total');
    var warnEl = el.querySelector('#history-warning');
    var listEl = el.querySelector('#history-list');
    var statusEl = el.querySelector('#history-status');

    var items = [];
    var vlist = null;
    var playingId = null;

    function setStatus(msg, isErr) {
      statusEl.textContent = msg || '';
      statusEl.style.color = isErr ? '#b00020' : '';
    }

    function rowHtml(it) {
      var name = (it.text_preview || it.id || 'Bản ghi').slice(0, 60);
      var playing = playingId === it.id ? ' ⏸ Đang phát' : '';
      var srtBtn = it.srt_path
        ? ' <button type="button" data-srt="' + esc(it.id) + '">Tải SRT</button>' : '';
      return '<strong>' + esc(name) + '</strong>'
        + ' — Giọng: ' + esc(it.voice_id || '?')
        + ' — Engine: ' + esc(it.engine || '?')
        + ' — ' + (it.duration_sec != null ? Number(it.duration_sec).toFixed(1) + ' s' : '?')
        + ' — ' + fmtBytes(it.size_bytes)
        + ' — ' + fmtDate(it.created_at) + playing
        + ' <button type="button" data-play="' + esc(it.id) + '">Nghe lại</button>'
        + ' <button type="button" data-dl="' + esc(it.id) + '">Tải ' + esc((it.format || 'wav').toUpperCase()) + '</button>'
        + srtBtn
        + ' <button type="button" data-open="' + esc(it.id) + '">Mở thư mục</button>'
        + ' <button type="button" data-del="' + esc(it.id) + '">Xoá</button>';
    }

    function bindRowButtons() {
      Array.prototype.forEach.call(listEl.querySelectorAll('[data-play]'), function (btn) {
        btn.addEventListener('click', function () { playItem(btn.getAttribute('data-play')); });
      });
      Array.prototype.forEach.call(listEl.querySelectorAll('[data-dl]'), function (btn) {
        btn.addEventListener('click', function () { downloadItem(btn.getAttribute('data-dl')); });
      });
      Array.prototype.forEach.call(listEl.querySelectorAll('[data-srt]'), function (btn) {
        btn.addEventListener('click', function () {
          setStatus('File SRT kèm theo nằm cùng thư mục với file audio — bấm "Mở thư mục" để lấy file .srt của bản này.', false);
        });
      });
      Array.prototype.forEach.call(listEl.querySelectorAll('[data-open]'), function (btn) {
        btn.addEventListener('click', function () { openFolder(btn.getAttribute('data-open')); });
      });
      Array.prototype.forEach.call(listEl.querySelectorAll('[data-del]'), function (btn) {
        btn.addEventListener('click', function () { deleteItem(btn.getAttribute('data-del')); });
      });
    }

    function refreshList() {
      if (vlist) { vlist.setItems(items); }
      else { listEl.innerHTML = items.map(rowHtml).join(''); }
      bindRowButtons();
    }

    function ensureList() {
      if (typeof NS.VirtualList === 'function') {
        listEl.innerHTML = '';
        vlist = new NS.VirtualList(listEl, {
          itemHeight: 44, items: items, overscan: 5,
          renderItem: function (it) { return rowHtml(it); }
        });
      } else {
        listEl.innerHTML = items.map(rowHtml).join('');
      }
      bindRowButtons();
    }

    function loadHistory() {
      totalEl.textContent = 'Đang tải…';
      warnEl.style.display = 'none';
      hpFetch('/api/history?limit=500&offset=0').then(function (resp) {
        if (!resp.ok) { return resp.text().then(function (t) { throw new Error('API trả ' + resp.status + ': ' + t); }); }
        return resp.json();
      }).then(function (data) {
        items = Array.isArray(data.items) ? data.items : [];
        var totalBytes = Number(data.total_bytes) || 0;
        var maxGb = Number(data.max_history_gb) || 5;
        var maxBytes = maxGb * 1e9;
        totalEl.textContent = 'Tổng cộng ' + (data.total || items.length) + ' bản — '
          + fmtBytes(totalBytes) + ' / giới hạn ' + maxGb + ' GB.';
        if (totalBytes >= maxBytes) {
          // TH-16: vượt giới hạn thì chặn tạo mới (server thực thi) + báo rõ.
          warnEl.style.display = '';
          warnEl.textContent = '⚠️ Đã vượt giới hạn lịch sử ' + maxGb + ' GB (' + fmtBytes(totalBytes) + '). '
            + 'Server sẽ CHẶN tạo bản mới cho tới khi bạn xoá hoặc xuất bớt bản cũ. '
            + 'Hãy xoá các bản không cần nữa ở danh sách bên dưới.';
        }
        if (!items.length) {
          listEl.innerHTML = '<p>Chưa có bản nào được tạo.</p>';
          return;
        }
        if (vlist) { refreshList(); } else { ensureList(); }
      }).catch(function (e) {
        totalEl.textContent = '';
        listEl.innerHTML = '<p>Không tải được lịch sử: ' + esc(e.message) + '</p>';
      });
    }

    function playItem(id) {
      var it = items.find(function (x) { return x.id === id; });
      if (!it) { return; }
      if (NS.player) {
        playingId = id;
        refreshList();
        NS.player.play(API_BASE + '/api/history/' + encodeURIComponent(id), 'Bản ' + id)
          .catch(function (e) { setStatus('Không phát được: ' + e.message, true); });
        NS.player.onStateChange(function (s) {
          if (s.paused && playingId === id) { playingId = null; refreshList(); }
        });
      }
      setStatus('Đang nghe lại bản "' + (it.text_preview || id).slice(0, 40) + '"…');
    }

    function downloadItem(id) {
      var it = items.find(function (x) { return x.id === id; });
      if (!it) { return; }
      var a = document.createElement('a');
      a.href = API_BASE + '/api/history/' + encodeURIComponent(id);
      a.download = 'hp-voice-' + id + '.' + (it.format || 'wav');
      a.click();
      setStatus('Đang tải lại bản "' + id + '".');
    }

    function openFolder(id) {
      var it = items.find(function (x) { return x.id === id; });
      if (!it) { return; }
      // Bản web chạy trong trình duyệt không được phép mở thư mục hệ thống.
      // Hiện rõ đường dẫn để người dùng tự mở; bản desktop (pywebview) sẽ
      // mở thư mục thật bằng nút này.
      var path = it.audio_path || ('(thư mục history)/' + id);
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(String(path)).then(function () {
          setStatus('Đường dẫn file: ' + path + ' — đã sao chép, hãy dán vào trình quản lý file để mở thư mục.', false);
        }, function () {
          setStatus('Đường dẫn file: ' + path, false);
        });
      } else {
        setStatus('Đường dẫn file: ' + path, false);
      }
    }

    function deleteItem(id) {
      var it = items.find(function (x) { return x.id === id; });
      if (!window.confirm('Xoá bản "' + (it && it.text_preview ? it.text_preview.slice(0, 40) : id) + '"? File audio sẽ bị xoá khỏi đĩa.')) { return; }
      hpFetch('/api/history/' + encodeURIComponent(id), { method: 'DELETE' })
        .then(function (resp) {
          if (resp.status === 204 || resp.ok) {
            setStatus('Đã xoá bản "' + id + '".');
            loadHistory();
          } else if (resp.status === 404) {
            setStatus('Không còn bản "' + id + '" (có thể đã xoá trước đó).', true);
            loadHistory();
          } else {
            return resp.text().then(function (t) { throw new Error('API trả ' + resp.status + ': ' + t); });
          }
        })
        .catch(function (e) { setStatus('Không xoá được: ' + e.message, true); });
    }

    el.querySelector('#history-refresh').addEventListener('click', loadHistory);

    loadHistory();
  }

  registerTab({ id: 'history', group: 'Thư viện', label: 'Bản đã tạo', render: render });
})();
