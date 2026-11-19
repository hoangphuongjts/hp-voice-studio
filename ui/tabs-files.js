/* HP Voice Studio — Tab Đọc file (TK3.3, test T3.4, SPEC §5).
 *
 * - Thả PDF/DOCX/TXT (POST /api/files/read, multipart) → xem trước text.
 * - Làm sạch: bỏ khoảng trắng thừa, giữ công thức (không gộp dòng công thức,
 *   không xoá ký tự toán học) — làm phía client trên text đã đọc.
 * - Chuyển sang Phòng thu tạo giọng: đẩy text sang tab Phòng thu qua
 *   window.HPVoiceStudio.openStudio(text) (hàm của agent TK3-UI-CORE);
 *   nếu chưa có thì báo rõ + sao chép text để dán tay.
 * - PDF scan → server trả 400 "v1 không OCR": UI hiện rõ câu đó, KHÔNG bịa text.
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

  /** Làm sạch text: bỏ khoảng trắng thừa, giữ nguyên công thức.
   * Giữ dòng chứa ký tự công thức (=, +, −, ×, ÷, ^, √, ∫, %) nguyên vẹn;
   * các dòng thường thì gộp khoảng trắng trong dòng + bỏ dòng trống thừa. */
  function cleanText(text) {
    var formulaRe = /[=+\-−×÷^√∫%<>≤≥]/;
    return String(text || '').replace(/\r\n/g, '\n').split('\n').map(function (line) {
      if (formulaRe.test(line)) { return line.replace(/[ \t]+/g, ' ').trim(); }
      return line.replace(/\s+/g, ' ').trim();
    }).join('\n').replace(/\n{3,}/g, '\n\n').trim();
  }

  function render(el) {
    el.innerHTML =
      '<h2>Đọc file</h2>'
      + '<p class="hp-hint">Đọc PDF, DOCX, TXT rồi chuyển sang Phòng thu để tạo giọng. '
      + 'File PDF scan (chỉ có ảnh, không có lớp chữ) sẽ được báo rõ là "v1 không OCR" — app không bịa text.</p>'
      + '<div id="file-drop" class="hp-drop">Kéo thả file PDF/DOCX/TXT vào đây, hoặc '
      + '<label class="hp-file-label">chọn file <input id="file-input" type="file" accept=".pdf,.docx,.txt"></label></div>'
      + '<div class="hp-row"><button id="file-clean" type="button" disabled>Làm sạch</button>'
      + '<button id="file-to-studio" type="button" disabled>Chuyển sang Phòng thu tạo giọng</button></div>'
      + '<p id="file-meta"></p>'
      + '<h3>Xem trước text</h3>'
      + '<textarea id="file-preview" rows="14" readonly placeholder="Chưa có file nào được đọc."></textarea>'
      + '<p id="file-status" role="status"></p>';

    var dropEl = el.querySelector('#file-drop');
    var inputEl = el.querySelector('#file-input');
    var previewEl = el.querySelector('#file-preview');
    var metaEl = el.querySelector('#file-meta');
    var statusEl = el.querySelector('#file-status');
    var cleanBtn = el.querySelector('#file-clean');
    var toStudioBtn = el.querySelector('#file-to-studio');

    var currentText = '';
    var currentFileName = '';

    function setStatus(msg, isErr) {
      statusEl.textContent = msg || '';
      statusEl.style.color = isErr ? '#b00020' : '';
    }

    function readFile(file) {
      if (!file) { return; }
      if (!/\.(pdf|docx|txt)$/i.test(file.name)) {
        setStatus('Chỉ nhận file PDF/DOCX/TXT.', true); return;
      }
      currentFileName = file.name;
      setStatus('Đang đọc "' + file.name + '"… (POST /api/files/read)');
      var form = new FormData();
      form.append('file', file);
      hpFetch('/api/files/read', { method: 'POST', body: form })
        .then(function (resp) {
          return resp.json().then(function (data) {
            if (!resp.ok) {
              var msg = (data && data.error && data.error.message) || data.detail || ('API trả ' + resp.status);
              throw new Error(String(msg));
            }
            return data;
          });
        })
        .then(function (data) {
          currentText = data.text || '';
          previewEl.value = currentText;
          previewEl.readOnly = false;
          var warnings = (data.warnings || []).join(' ');
          metaEl.textContent = 'File: ' + currentFileName + ' — loại ' + (data.kind || '?')
            + (data.pages ? ' — ' + data.pages + ' trang' : '')
            + ' — ' + (data.chars || currentText.length) + ' ký tự'
            + (warnings ? ' — Lưu ý: ' + warnings : '');
          cleanBtn.disabled = false;
          toStudioBtn.disabled = false;
          setStatus('Đã đọc xong "' + currentFileName + '". Bấm "Làm sạch" để bỏ khoảng trắng thừa, '
            + 'rồi "Chuyển sang Phòng thu" để tạo giọng.');
        })
        .catch(function (e) {
          // PDF scan: server trả 400 kèm "v1 không OCR" — hiện nguyên văn, không bịa text.
          var isScan = /không OCR|scan/i.test(e.message);
          setStatus((isScan
            ? 'File "' + currentFileName + '" là PDF scan (chỉ có ảnh, không có lớp chữ): v1 không OCR nên không trích được text. Hãy dùng bản PDF có lớp chữ hoặc gõ lại nội dung.'
            : 'Không đọc được file: ' + e.message), true);
          previewEl.value = '';
          cleanBtn.disabled = true;
          toStudioBtn.disabled = true;
        });
    }

    inputEl.addEventListener('change', function (e) { readFile(e.target.files[0]); });
    ['dragover', 'dragenter'].forEach(function (evt) {
      dropEl.addEventListener(evt, function (e) { e.preventDefault(); dropEl.classList.add('hp-drop-over'); });
    });
    ['dragleave', 'drop'].forEach(function (evt) {
      dropEl.addEventListener(evt, function (e) { e.preventDefault(); dropEl.classList.remove('hp-drop-over'); });
    });
    dropEl.addEventListener('drop', function (e) {
      var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      readFile(f);
    });

    cleanBtn.addEventListener('click', function () {
      var before = previewEl.value;
      var cleaned = cleanText(before);
      previewEl.value = cleaned;
      currentText = cleaned;
      setStatus('Đã làm sạch: bỏ khoảng trắng thừa, giữ nguyên dòng công thức. '
        + 'Trước: ' + before.length + ' ký tự → sau: ' + cleaned.length + ' ký tự.');
    });

    previewEl.addEventListener('input', function () { currentText = previewEl.value; });

    toStudioBtn.addEventListener('click', function () {
      var text = (previewEl.value || '').trim();
      if (!text) { setStatus('Không có text để chuyển sang Phòng thu.', true); return; }
      if (typeof NS.openStudio === 'function') {
        NS.openStudio(text);
        setStatus('Đã chuyển text sang tab Phòng thu — bấm Tạo để tạo giọng.');
      } else {
        // openStudio là hàm của agent TK3-UI-CORE (ui/app.js); chưa có thì
        // sao chép text để người dùng dán tay, không im lặng mất text.
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(function () {
            setStatus('Tab Phòng thu chưa cung cấp hàm openStudio — đã sao chép text vào clipboard, '
              + 'hãy mở tab Phòng thu và dán vào ô nhập text.', true);
          }, function () {
            setStatus('Tab Phòng thu chưa cung cấp hàm openStudio — hãy mở tab Phòng thu và dán text đã đọc vào.', true);
          });
        } else {
          setStatus('Tab Phòng thu chưa cung cấp hàm openStudio — hãy mở tab Phòng thu và dán text đã đọc vào.', true);
        }
      }
    });
  }

  // Xuất helper để test tĩnh / dùng lại: làm sạch giữ công thức.
  NS.cleanFileText = cleanText;

  registerTab({ id: 'files', group: 'Tạo', label: 'Đọc file', render: render });
})();
