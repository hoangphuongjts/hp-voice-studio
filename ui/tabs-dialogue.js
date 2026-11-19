/* HP Voice Studio — Tab Hội thoại / Podcast (TK3.2, test T3.2, SPEC §5).
 *
 * - Bảng kịch bản: mỗi dòng (nhân vật, lời thoại).
 * - Mỗi nhân vật gán 1 giọng CỐ ĐỊNH (dropdown + khoá 🔒): voice-lock theo
 *   TH-10 — giọng không được trôi/lẫn giữa các lượt, kể cả khi mở lại kịch bản.
 * - Thêm/xoá nhân vật, tối đa 8 (MAX_SPEAKERS của ConversationEngine).
 * - Khoảng lặng giữa lượt (pause_s), ghép thành 1 file qua POST /api/tts/conversation.
 * - Lưu/mở kịch bản JSON (giữ mapping nhân vật → giọng, T3.2 đo bằng voice_id
 *   trong file đã lưu, không chỉ nghe bằng tai).
 */
(function () {
  'use strict';

  var NS = window.HPVoiceStudio = window.HPVoiceStudio || {};
  var API_BASE = 'http://127.0.0.1:8124';
  var MAX_SPEAKERS = 8;

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

  function render(el) {
    // Trạng thái tab (chỉ sống trong tab, không ghi ra ngoài).
    var state = {
      speakers: [
        { name: 'Người 1', voice: 'Hải Đăng', locked: false },
        { name: 'Người 2', voice: 'Mai Anh', locked: false }
      ],
      lines: [
        { speaker: 'Người 1', text: 'Xin chào các bạn, hôm nay mình có một món rất hay muốn giới thiệu.' },
        { speaker: 'Người 2', text: 'Ồ, món gì thế? Cho mình xem với.' },
        { speaker: 'Người 1', text: 'Đây này, dùng thử là thích ngay.' }
      ],
      pause_s: 0.5,
      voices: [],
      busy: false
    };

    el.innerHTML =
      '<h2>Hội thoại / Podcast</h2>'
      + '<p class="hp-hint">Mỗi nhân vật gán 1 giọng cố định và khoá lại — giọng không đổi '
      + 'xuyên suốt kịch bản và khi mở lại file (voice-lock, TH-10).</p>'
      + '<div class="hp-row"><label>Khoảng lặng giữa lượt (giây) '
      + '<input id="dlg-pause" type="number" min="0" max="5" step="0.1" value="0.5"></label>'
      + '<button id="dlg-add-speaker" type="button">+ Thêm nhân vật</button>'
      + '<button id="dlg-add-line" type="button">+ Thêm lượt thoại</button></div>'
      + '<h3>Nhân vật (tối đa ' + MAX_SPEAKERS + ')</h3>'
      + '<div id="dlg-speakers"></div>'
      + '<h3>Kịch bản</h3>'
      + '<table class="hp-table"><thead><tr><th>Nhân vật</th><th>Lời thoại</th><th></th></tr></thead>'
      + '<tbody id="dlg-lines"></tbody></table>'
      + '<div class="hp-row"><button id="dlg-create" type="button">Ghép thành 1 file</button>'
      + '<button id="dlg-save" type="button">Lưu kịch bản (.json)</button>'
      + '<label class="hp-file-label">Mở kịch bản <input id="dlg-load" type="file" accept=".json,application/json"></label>'
      + '<button id="dlg-play" type="button" disabled>Nghe lại</button></div>'
      + '<p id="dlg-status" role="status"></p>';

    var speakersEl = el.querySelector('#dlg-speakers');
    var linesEl = el.querySelector('#dlg-lines');
    var statusEl = el.querySelector('#dlg-status');
    var lastBlob = null;
    var lastBlobUrl = null;

    function setStatus(msg, isErr) {
      statusEl.textContent = msg || '';
      statusEl.style.color = isErr ? '#b00020' : '';
    }

    function voiceOptions(selected) {
      var opts = '<option value="">— Chọn giọng —</option>';
      state.voices.forEach(function (v) {
        opts += '<option value="' + esc(v.id) + '"' + (v.id === selected ? ' selected' : '') + '>'
          + esc(v.name || v.id)
          + (v.gender ? ' (' + esc(v.gender) + ')' : '')
          + (v.is_clone ? ' [clone]' : '') + '</option>';
      });
      return opts;
    }

    function drawSpeakers() {
      speakersEl.innerHTML = state.speakers.map(function (sp, i) {
        return '<div class="hp-row" data-speaker="' + i + '">'
          + '<input class="dlg-spk-name" type="text" value="' + esc(sp.name) + '" placeholder="Tên nhân vật" aria-label="Tên nhân vật">'
          + '<select class="dlg-spk-voice" aria-label="Giọng của ' + esc(sp.name) + '"' + (sp.locked ? ' disabled' : '') + '>'
          + voiceOptions(sp.voice) + '</select>'
          + '<label><input class="dlg-spk-lock" type="checkbox"' + (sp.locked ? ' checked' : '') + '> Khoá giọng 🔒</label>'
          + '<button type="button" class="dlg-spk-del">Xoá</button></div>';
      }).join('') || '<p>Chưa có nhân vật nào.</p>';
      // Gắn sự kiện sau khi vẽ (innerHTML làm mất listener cũ).
      Array.prototype.forEach.call(speakersEl.querySelectorAll('[data-speaker]'), function (row) {
        var i = Number(row.getAttribute('data-speaker'));
        row.querySelector('.dlg-spk-name').addEventListener('change', function (e) {
          var oldName = state.speakers[i].name;
          var next = e.target.value.trim();
          if (!next) { e.target.value = oldName; setStatus('Tên nhân vật không được để trống.', true); return; }
          if (state.speakers.some(function (s, j) { return j !== i && s.name === next; })) {
            e.target.value = oldName; setStatus('Đã có nhân vật tên "' + next + '".', true); return;
          }
          state.speakers[i].name = next;
          state.lines.forEach(function (ln) { if (ln.speaker === oldName) { ln.speaker = next; } });
          drawLines();
        });
        row.querySelector('.dlg-spk-voice').addEventListener('change', function (e) {
          state.speakers[i].voice = e.target.value;
        });
        row.querySelector('.dlg-spk-lock').addEventListener('change', function (e) {
          state.speakers[i].locked = e.target.checked;
          if (e.target.checked && !state.speakers[i].voice) {
            setStatus('Khoá giọng cần chọn giọng trước cho "' + state.speakers[i].name + '".', true);
            state.speakers[i].locked = false; e.target.checked = false; return;
          }
          drawSpeakers();
        });
        row.querySelector('.dlg-spk-del').addEventListener('click', function () {
          var name = state.speakers[i].name;
          if (state.lines.some(function (ln) { return ln.speaker === name; })) {
            setStatus('Nhân vật "' + name + '" còn lượt thoại trong kịch bản — xoá các lượt đó trước.', true);
            return;
          }
          state.speakers.splice(i, 1);
          drawSpeakers();
        });
      });
    }

    function drawLines() {
      linesEl.innerHTML = state.lines.map(function (ln, i) {
        var opts = state.speakers.map(function (sp) {
          return '<option value="' + esc(sp.name) + '"' + (sp.name === ln.speaker ? ' selected' : '') + '>'
            + esc(sp.name) + ' — ' + esc(sp.voice || 'chưa gán giọng') + '</option>';
        }).join('');
        return '<tr data-line="' + i + '"><td><select class="dlg-line-spk" aria-label="Nhân vật lượt ' + (i + 1) + '">'
          + opts + '</select></td>'
          + '<td><textarea class="dlg-line-text" rows="2" placeholder="Lời thoại…">' + esc(ln.text) + '</textarea></td>'
          + '<td><button type="button" class="dlg-line-del">Xoá</button></td></tr>';
      }).join('');
      Array.prototype.forEach.call(linesEl.querySelectorAll('[data-line]'), function (row) {
        var i = Number(row.getAttribute('data-line'));
        row.querySelector('.dlg-line-spk').addEventListener('change', function (e) {
          state.lines[i].speaker = e.target.value;
        });
        row.querySelector('.dlg-line-text').addEventListener('change', function (e) {
          state.lines[i].text = e.target.value;
        });
        row.querySelector('.dlg-line-del').addEventListener('click', function () {
          state.lines.splice(i, 1);
          drawLines();
        });
      });
    }

    function validate() {
      if (state.speakers.length === 0) { return 'Chưa có nhân vật nào.'; }
      if (state.speakers.length > MAX_SPEAKERS) { return 'Tối đa ' + MAX_SPEAKERS + ' nhân vật.'; }
      var missing = state.speakers.filter(function (sp) { return !sp.voice; });
      if (missing.length) {
        return 'Nhân vật chưa gán giọng: ' + missing.map(function (sp) { return '"' + sp.name + '"'; }).join(', ')
          + ' — mỗi nhân vật phải có 1 giọng cố định trước khi tạo.';
      }
      if (state.lines.length === 0) { return 'Kịch bản chưa có lượt thoại nào.'; }
      var empty = state.lines.findIndex(function (ln) { return !ln.text.trim(); });
      if (empty >= 0) { return 'Lượt thoại số ' + (empty + 1) + ' đang trống.'; }
      return null;
    }

    function toScript() {
      var speakers = {};
      state.speakers.forEach(function (sp) { speakers[sp.name] = sp.voice; });
      return {
        title: 'Kịch bản hội thoại',
        pause_s: state.pause_s,
        speakers: speakers,
        lines: state.lines.map(function (ln) { return { speaker: ln.speaker, text: ln.text }; })
      };
    }

    el.querySelector('#dlg-pause').addEventListener('change', function (e) {
      state.pause_s = Math.min(5, Math.max(0, parseFloat(e.target.value) || 0));
    });

    el.querySelector('#dlg-add-speaker').addEventListener('click', function () {
      if (state.speakers.length >= MAX_SPEAKERS) {
        setStatus('Đã đủ tối đa ' + MAX_SPEAKERS + ' nhân vật.', true); return;
      }
      state.speakers.push({ name: 'Người ' + (state.speakers.length + 1), voice: '', locked: false });
      drawSpeakers(); drawLines();
      setStatus('');
    });

    el.querySelector('#dlg-add-line').addEventListener('click', function () {
      if (!state.speakers.length) { setStatus('Thêm nhân vật trước khi thêm lượt thoại.', true); return; }
      state.lines.push({ speaker: state.speakers[0].name, text: '' });
      drawLines();
    });

    el.querySelector('#dlg-create').addEventListener('click', function () {
      var err = validate();
      if (err) { setStatus(err, true); return; }
      state.busy = true;
      setStatus('Đang ghép hội thoại… (POST /api/tts/conversation)');
      hpFetch('/api/tts/conversation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lines: state.lines, speakers: toScript().speakers,
          format: 'wav', pause_s: state.pause_s
        })
      }).then(function (resp) {
        if (!resp.ok) { return resp.text().then(function (t) { throw new Error('API trả ' + resp.status + ': ' + t); }); }
        return resp.blob();
      }).then(function (blob) {
        lastBlob = blob;
        if (lastBlobUrl) { URL.revokeObjectURL(lastBlobUrl); }
        lastBlobUrl = URL.createObjectURL(blob);
        el.querySelector('#dlg-play').disabled = false;
        setStatus('Đã ghép xong 1 file WAV (' + state.lines.length + ' lượt, '
          + state.speakers.length + ' nhân vật). Bấm "Nghe lại" hoặc tải file.');
        var a = document.createElement('a');
        a.href = lastBlobUrl; a.download = 'hoi-thoai.wav'; a.click();
      }).catch(function (e) {
        setStatus('Không tạo được hội thoại: ' + e.message, true);
      }).finally(function () { state.busy = false; });
    });

    el.querySelector('#dlg-play').addEventListener('click', function () {
      if (lastBlobUrl && NS.player) { NS.player.play(lastBlobUrl, 'Hội thoại'); }
    });

    el.querySelector('#dlg-save').addEventListener('click', function () {
      var blob = new Blob([JSON.stringify(toScript(), null, 2)], { type: 'application/json' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url; a.download = 'kich-ban-hoi-thoai.json'; a.click();
      setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
      setStatus('Đã lưu kịch bản JSON (giữ nguyên mapping nhân vật → giọng).');
    });

    el.querySelector('#dlg-load').addEventListener('change', function (e) {
      var file = e.target.files && e.target.files[0];
      if (!file) { return; }
      var reader = new FileReader();
      reader.onload = function () {
        try {
          var data = JSON.parse(String(reader.result));
          if (!data.speakers || !Array.isArray(data.lines)) { throw new Error('File không đúng định dạng kịch bản.'); }
          state.speakers = Object.keys(data.speakers).map(function (name) {
            return { name: name, voice: data.speakers[name], locked: true };
          });
          state.lines = data.lines.map(function (ln) { return { speaker: ln.speaker, text: ln.text }; });
          state.pause_s = typeof data.pause_s === 'number' ? data.pause_s : 0.5;
          el.querySelector('#dlg-pause').value = String(state.pause_s);
          drawSpeakers(); drawLines();
          setStatus('Đã mở kịch bản: ' + state.lines.length + ' lượt, giọng các nhân vật đã khoá lại như file đã lưu.');
        } catch (err) { setStatus('Không mở được kịch bản: ' + err.message, true); }
      };
      reader.readAsText(file);
      e.target.value = '';
    });

    // Nạp danh sách giọng (preset + clone) để gán cho nhân vật.
    hpFetch('/voices?engine=v3').then(function (resp) {
      return resp.ok ? resp.json() : [];
    }).then(function (list) {
      state.voices = Array.isArray(list) ? list : [];
      drawSpeakers(); drawLines();
    }).catch(function () {
      state.voices = [];
      drawSpeakers(); drawLines();
      setStatus('Không tải được danh sách giọng từ API — kiểm tra server 127.0.0.1:8124 đang chạy.', true);
    });

    drawSpeakers();
    drawLines();
  }

  registerTab({ id: 'dialogue', group: 'Tạo', label: 'Hội thoại / Podcast', render: render });
})();
