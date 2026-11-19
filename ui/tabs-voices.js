/* HP Voice Studio — Tab Giọng của tôi (TK3.2, test T2.5, SPEC §5 + TH-04/TH-17).
 *
 * - Danh sách giọng clone (tên, ngày tạo, cam kết) — đọc từ GET /voices, lọc is_clone.
 * - Tạo giọng mới: thu micro 3–8 s (MediaRecorder + getUserMedia, đếm ngược 8 s,
 *   tự dừng; trình duyệt từ chối quyền micro thì báo rõ) HOẶC nhập file
 *   MP3/WAV/M4A (Q13 = CẢ 2).
 * - Màn hình cam kết quyền sử dụng: BẮT BUỘC tick checkbox + nhập tên chủ giọng
 *   trước khi bấm "Tạo giọng". Ghi chú pháp lý: giọng nói là dữ liệu cá nhân
 *   (Nghị định 13/2023), nội dung AI phải ghi nhãn (Nghị định 147/2024).
 * - Nghe thử (GET /voices/{id}/preview qua player dùng chung), xoá (xoá cùng
 *   cam kết; có cơ chế gỡ khi bị khiếu nại — TH-17).
 *
 * ⚠️ ENDPOINT CÒN THIẾU (ghi rõ để coordinator bổ sung — tab KHÔNG tự thêm
 * endpoint): API hiện chưa có `POST /api/voices/clone` (endpoint 10 trong
 * docs/api-contract.md, thuộc TK3.2 cùng tab này) và chưa có endpoint xoá
 * giọng clone. Logic clone đã có sẵn ở `VoiceStore.clone_voice` / `takedown`
 * (TK1.5). Tab vẫn gửi đúng request theo hợp đồng (multipart: audio + name +
 * consent + consent_text + owner) và báo rõ 404 = "API chưa có endpoint",
 * không bịa là đã tạo xong.
 */
(function () {
  'use strict';

  var NS = window.HPVoiceStudio = window.HPVoiceStudio || {};
  var API_BASE = 'http://127.0.0.1:8124';
  var MIN_CLIP_S = 3;
  var MAX_CLIP_S = 8;

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

  var CONSENT_TEXT = 'Tôi cam kết clip mẫu này là giọng của chính tôi hoặc tôi đã được '
    + 'chủ giọng đồng ý cho dùng để tạo giọng đọc AI trong HP Voice Studio '
    + '(dùng cá nhân, không phát tán khi chưa được phép).';

  function render(el) {
    el.innerHTML =
      '<h2>Giọng của tôi</h2>'
      + '<p class="hp-hint">Giọng clone chỉ lưu trên máy của bạn, không đồng bộ cloud, '
      + 'không xuất file mẫu gốc. Giọng nói là dữ liệu cá nhân theo Nghị định 13/2023; '
      + 'nội dung dùng giọng AI phải ghi nhãn theo Nghị định 147/2024.</p>'
      + '<h3>Danh sách giọng clone</h3>'
      + '<div id="voice-list"><p>Đang tải…</p></div>'
      + '<button id="voice-refresh" type="button">Tải lại danh sách</button>'
      + '<h3>Tạo giọng mới</h3>'
      + '<div class="hp-row"><label>Tên giọng mới '
      + '<input id="voice-name" type="text" placeholder="VD: Giọng của tôi"></label>'
      + '<label>Tên chủ giọng '
      + '<input id="voice-owner" type="text" placeholder="Tên người sở hữu giọng"></label></div>'
      + '<div class="hp-row"><button id="voice-record" type="button">● Thu micro 3–8 s</button>'
      + '<button id="voice-stop" type="button" disabled>Dừng thu</button>'
      + '<span id="voice-countdown" aria-live="polite"></span></div>'
      + '<p class="hp-hint">Thu micro: bấm thu rồi nói liên tục 3–8 giây, máy tự dừng ở 8 giây. '
      + 'Nếu trình duyệt hỏi quyền micro, hãy chọn Cho phép — từ chối quyền thì không thu được.</p>'
      + '<div class="hp-row"><label>…hoặc nhập file mẫu (Q13 = cả 2 cách) '
      + '<input id="voice-file" type="file" accept=".mp3,.wav,.m4a,audio/*"></label>'
      + '<span id="voice-file-info"></span></div>'
      + '<div class="hp-row"><button id="voice-preview-clip" type="button" disabled>Nghe thử clip mẫu</button></div>'
      + '<fieldset><legend>Cam kết quyền sử dụng (bắt buộc)</legend>'
      + '<label><input id="voice-consent" type="checkbox"> ' + esc(CONSENT_TEXT) + '</label>'
      + '<p class="hp-hint">Cam kết này là lời hứa, không phải xác minh danh tính. '
      + 'Chỉ clone giọng của chính bạn hoặc giọng đã được chủ giọng đồng ý.</p></fieldset>'
      + '<div class="hp-row"><button id="voice-create" type="button" disabled>Tạo giọng</button></div>'
      + '<p class="hp-hint">Cơ chế gỡ khi bị khiếu nại: giọng bị khiếu nại sẽ bị gỡ khỏi app '
      + 'cùng toàn bộ cam kết kèm theo (ghi log gỡ) — xem nút "Gỡ (khiếu nại)" ở mỗi giọng.</p>'
      + '<p id="voice-status" role="status"></p>';

    var listEl = el.querySelector('#voice-list');
    var statusEl = el.querySelector('#voice-status');
    var consentEl = el.querySelector('#voice-consent');
    var ownerEl = el.querySelector('#voice-owner');
    var nameEl = el.querySelector('#voice-name');
    var fileEl = el.querySelector('#voice-file');
    var countdownEl = el.querySelector('#voice-countdown');
    var createBtn = el.querySelector('#voice-create');
    var previewClipBtn = el.querySelector('#voice-preview-clip');

    var clipBlob = null;      // Blob clip mẫu (thu micro hoặc file nhập)
    var clipName = '';
    var recorder = null;
    var recordTimer = null;
    var recordStartedAt = 0;
    var recordStream = null;

    function setStatus(msg, isErr) {
      statusEl.textContent = msg || '';
      statusEl.style.color = isErr ? '#b00020' : '';
    }

    function updateCreateState() {
      var ok = consentEl.checked && ownerEl.value.trim() !== '' && nameEl.value.trim() !== ''
        && !!clipBlob;
      createBtn.disabled = !ok;
      previewClipBtn.disabled = !clipBlob;
      if (!ok) {
        var thieu = [];
        if (!clipBlob) { thieu.push('clip mẫu 3–8 s'); }
        if (!nameEl.value.trim()) { thieu.push('tên giọng'); }
        if (!ownerEl.value.trim()) { thieu.push('tên chủ giọng'); }
        if (!consentEl.checked) { thieu.push('tick cam kết'); }
        createBtn.title = 'Còn thiếu: ' + thieu.join(', ') + '.';
      } else { createBtn.title = ''; }
    }

    [consentEl, ownerEl, nameEl].forEach(function (input) {
      input.addEventListener('input', updateCreateState);
      input.addEventListener('change', updateCreateState);
    });

    function loadClones() {
      listEl.innerHTML = '<p>Đang tải…</p>';
      hpFetch('/voices?engine=v3').then(function (resp) {
        if (!resp.ok) { throw new Error('API trả ' + resp.status); }
        return resp.json();
      }).then(function (list) {
        var clones = (Array.isArray(list) ? list : []).filter(function (v) { return v.is_clone; });
        if (!clones.length) {
          listEl.innerHTML = '<p>Chưa có giọng clone nào. Tạo giọng mới ở bên dưới.</p>';
          return;
        }
        listEl.innerHTML = clones.map(function (v) {
          return '<div class="hp-row" data-voice="' + esc(v.id) + '">'
            + '<strong>' + esc(v.name || v.id) + '</strong>'
            + '<span>Ngày tạo: ' + esc(v.created_at || 'không rõ') + '</span>'
            + '<span>Cam kết: ' + esc(v.consent_text ? 'đã cam kết' : 'có cam kết kèm theo') + '</span>'
            + '<button type="button" class="voice-preview">Nghe thử</button>'
            + '<button type="button" class="voice-delete">Xoá</button>'
            + '<button type="button" class="voice-takedown">Gỡ (khiếu nại)</button></div>';
        }).join('');
        Array.prototype.forEach.call(listEl.querySelectorAll('[data-voice]'), function (row) {
          var id = row.getAttribute('data-voice');
          row.querySelector('.voice-preview').addEventListener('click', function () {
            if (NS.player) {
              NS.player.play(API_BASE + '/voices/' + encodeURIComponent(id) + '/preview',
                'Nghe thử giọng ' + id);
            }
            setStatus('Đang nghe thử giọng "' + id + '"…');
          });
          row.querySelector('.voice-delete').addEventListener('click', function () {
            deleteVoice(id, false);
          });
          row.querySelector('.voice-takedown').addEventListener('click', function () {
            if (!window.confirm('Gỡ giọng "' + id + '" vì khiếu nại? Giọng và cam kết kèm theo sẽ bị xoá, việc gỡ được ghi log.')) { return; }
            deleteVoice(id, true);
          });
        });
      }).catch(function (e) {
        listEl.innerHTML = '<p>Không tải được danh sách giọng: ' + esc(e.message) + '</p>';
      });
    }

    // Xoá giọng clone: API chưa có endpoint DELETE giọng clone (coordinator bổ sung).
    // Tab thử đúng đường dẫn theo hợp đồng, 404 thì báo rõ, không giả vờ đã xoá.
    function deleteVoice(id, isTakedown) {
      setStatus('Đang gửi yêu cầu xoá giọng "' + id + '"…');
      hpFetch('/api/voices/' + encodeURIComponent(id), { method: 'DELETE' })
        .then(function (resp) {
          if (resp.status === 204 || resp.ok) {
            setStatus('Đã xoá giọng "' + id + '"' + (isTakedown ? ' (gỡ theo khiếu nại — cam kết kèm theo đã xoá cùng).' : '.'));
            loadClones();
          } else if (resp.status === 404) {
            setStatus('API chưa có endpoint xoá giọng clone (DELETE /api/voices/{id}) — '
              + 'cần coordinator bổ sung. Logic gỡ đã có sẵn ở VoiceStore.takedown (TK1.5).', true);
          } else {
            return resp.text().then(function (t) { throw new Error('API trả ' + resp.status + ': ' + t); });
          }
        })
        .catch(function (e) { setStatus('Không xoá được giọng: ' + e.message, true); });
    }

    function stopRecording(manual) {
      if (recordTimer) { clearInterval(recordTimer); recordTimer = null; }
      if (recordStream) {
        recordStream.getTracks().forEach(function (t) { try { t.stop(); } catch (e) { /* bỏ qua */ } });
        recordStream = null;
      }
      if (recorder && recorder.state !== 'inactive') {
        try { recorder.stop(); } catch (e) { /* bỏ qua */ }
      }
      el.querySelector('#voice-record').disabled = false;
      el.querySelector('#voice-stop').disabled = true;
      if (manual) { countdownEl.textContent = ''; }
    }

    el.querySelector('#voice-record').addEventListener('click', function () {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setStatus('Trình duyệt này không hỗ trợ thu micro (thiếu getUserMedia). Hãy nhập file mẫu thay thế.', true);
        return;
      }
      if (!window.MediaRecorder) {
        setStatus('Trình duyệt này không hỗ trợ MediaRecorder. Hãy nhập file mẫu thay thế.', true);
        return;
      }
      setStatus('Đang xin quyền micro…');
      navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
        recordStream = stream;
        var chunks = [];
        recorder = new MediaRecorder(stream);
        recorder.ondataavailable = function (e) { if (e.data && e.data.size) { chunks.push(e.data); } };
        recorder.onstop = function () {
          var blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
          var seconds = (Date.now() - recordStartedAt) / 1000;
          clipBlob = blob;
          clipName = 'thu-micro.webm';
          countdownEl.textContent = 'Đã thu ' + seconds.toFixed(1) + ' s.'
            + (seconds < MIN_CLIP_S ? ' Clip ngắn hơn ' + MIN_CLIP_S + ' s — cần thu lại dài hơn.' : '')
            + (seconds > MAX_CLIP_S ? ' Clip dài hơn ' + MAX_CLIP_S + ' s — sẽ chỉ dùng ' + MAX_CLIP_S + ' s đầu.' : '');
          if (seconds < MIN_CLIP_S) { clipBlob = null; }
          setStatus(seconds < MIN_CLIP_S
            ? 'Clip chỉ dài ' + seconds.toFixed(1) + ' s, chưa đủ tối thiểu ' + MIN_CLIP_S + ' s — hãy thu lại.'
            : 'Đã có clip mẫu ' + seconds.toFixed(1) + ' s. Tick cam kết + nhập tên chủ giọng rồi bấm "Tạo giọng".');
          updateCreateState();
        };
        recorder.start();
        recordStartedAt = Date.now();
        el.querySelector('#voice-record').disabled = true;
        el.querySelector('#voice-stop').disabled = false;
        setStatus('Đang thu… nói liên tục, máy tự dừng ở ' + MAX_CLIP_S + ' giây.');
        var remaining = MAX_CLIP_S;
        countdownEl.textContent = 'Còn ' + remaining + ' s — tự dừng ở ' + MAX_CLIP_S + ' s.';
        recordTimer = setInterval(function () {
          remaining = MAX_CLIP_S - (Date.now() - recordStartedAt) / 1000;
          if (remaining <= 0) {
            countdownEl.textContent = 'Đã đủ ' + MAX_CLIP_S + ' s — tự dừng.';
            stopRecording(false);
          } else {
            countdownEl.textContent = 'Còn ' + remaining.toFixed(0) + ' s — tự dừng ở ' + MAX_CLIP_S + ' s.';
          }
        }, 200);
      }).catch(function (err) {
        // Trình duyệt từ chối quyền micro: báo rõ nguyên nhân + cách sửa, không im lặng.
        var reason = (err && err.name === 'NotAllowedError')
          ? 'Bạn đã từ chối quyền micro (hoặc trình duyệt chặn). Bấm biểu tượng ổ khoá/khóa bên cạnh địa chỉ trang để cho phép micro, rồi thu lại — hoặc nhập file mẫu thay thế.'
          : 'Không mở được micro: ' + (err && err.message ? err.message : err);
        setStatus(reason, true);
      });
    });

    el.querySelector('#voice-stop').addEventListener('click', function () { stopRecording(true); });

    fileEl.addEventListener('change', function (e) {
      var file = e.target.files && e.target.files[0];
      if (!file) { return; }
      var okExt = /\.(mp3|wav|m4a)$/i.test(file.name);
      if (!okExt) {
        setStatus('File mẫu chỉ nhận MP3/WAV/M4A.', true);
        e.target.value = '';
        return;
      }
      clipBlob = file;
      clipName = file.name;
      el.querySelector('#voice-file-info').textContent = 'Đã chọn: ' + file.name
        + ' (' + (file.size / 1024).toFixed(0) + ' KB). Server kiểm tra độ dài 3–8 s khi tạo giọng.';
      setStatus('Đã có clip mẫu từ file. Tick cam kết + nhập tên chủ giọng rồi bấm "Tạo giọng".');
      updateCreateState();
    });

    previewClipBtn.addEventListener('click', function () {
      if (clipBlob && NS.player) { NS.player.playBlob(clipBlob, 'Nghe thử clip mẫu'); }
    });

    createBtn.addEventListener('click', function () {
      if (!consentEl.checked) { setStatus('Chưa tick cam kết quyền sử dụng — không thể tạo giọng clone.', true); return; }
      if (!ownerEl.value.trim()) { setStatus('Chưa nhập tên chủ giọng.', true); return; }
      if (!clipBlob) { setStatus('Chưa có clip mẫu 3–8 s.', true); return; }
      var form = new FormData();
      form.append('audio', clipBlob, clipName || 'clip-mau');
      form.append('name', nameEl.value.trim());
      form.append('owner', ownerEl.value.trim());
      form.append('consent', 'true');
      form.append('consent_text', CONSENT_TEXT);
      setStatus('Đang tạo giọng "' + nameEl.value.trim() + '"… (POST /api/voices/clone)');
      hpFetch('/api/voices/clone', { method: 'POST', body: form })
        .then(function (resp) {
          if (resp.status === 404) {
            throw new Error('API chưa có endpoint POST /api/voices/clone (endpoint 10, docs/api-contract.md) — '
              + 'cần coordinator bổ sung. Logic clone đã có sẵn ở VoiceStore.clone_voice (TK1.5). '
              + 'Clip mẫu + cam kết của bạn chưa gửi đi đâu.');
          }
          if (!resp.ok) { return resp.text().then(function (t) { throw new Error('API trả ' + resp.status + ': ' + t); }); }
          return resp.json();
        })
        .then(function () {
          setStatus('Đã tạo giọng "' + nameEl.value.trim() + '" (cam kết đã lưu cùng giọng).');
          clipBlob = null; fileEl.value = '';
          updateCreateState();
          loadClones();
        })
        .catch(function (e) { setStatus('Không tạo được giọng: ' + e.message, true); });
    });

    el.querySelector('#voice-refresh').addEventListener('click', loadClones);

    updateCreateState();
    loadClones();
  }

  registerTab({ id: 'voices', group: 'Thư viện', label: 'Giọng của tôi', render: render });
})();
