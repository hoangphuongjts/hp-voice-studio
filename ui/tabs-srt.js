/* HP Voice Studio — Tab Lồng tiếng .srt (TK3.3, test T3.3, SPEC §5 + TH-07).
 *
 * - Thả file .srt/.vtt → danh sách câu + mốc giờ (parse phía client để xem trước).
 * - Chọn giọng + tốc độ (0,75×–1,5×) → bấm Lồng tiếng (POST /api/tts/srt-dub,
 *   multipart) → ZIP (dub.wav + dub.srt đã chỉnh mốc + report.json).
 * - Tiến trình từng câu (đánh dấu câu đang lồng theo thứ tự), kết quả: audio
 *   dài đúng bằng video + SRT đã chỉnh mốc + danh sách câu bị lùi.
 * - Quy tắc hiện rõ trong UI: câu dài đọc nhanh tối đa 1,5×, KHÔNG cắt chữ.
 *   Câu chưa vừa thì lấn khoảng lặng sau, rồi đẩy câu sau lùi (server báo
 *   trong report.json) — không bao giờ cắt chữ.
 */
(function () {
  'use strict';

  var NS = window.HPVoiceStudio = window.HPVoiceStudio || {};
  var API_BASE = 'http://127.0.0.1:8124';
  var MAX_RATE = 1.5;

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

  /* Đọc file ZIP tối thiểu (đủ để lấy dub.srt + report.json từ ZIP server trả):
   * parse End-Of-Central-Directory → central directory → giải nén từng entry
   * (stored/deflate) bằng DecompressionStream. Dùng chung cho tab SRT + Batch. */
  if (!NS.readZip) {
    NS.readZip = function (blob) {
      return blob.arrayBuffer().then(function (buf) {
        var view = new DataView(buf);
        // Tìm EOCD (signature 0x06054b50) từ cuối file.
        var eocd = -1;
        for (var p = buf.byteLength - 22; p >= 0; p--) {
          if (view.getUint32(p, true) === 0x06054b50) { eocd = p; break; }
        }
        if (eocd < 0) { throw new Error('File ZIP không đọc được (không thấy EOCD).'); }
        var count = view.getUint16(eocd + 10, true);
        var cdOffset = view.getUint32(eocd + 16, true);
        var entries = [];
        var pos = cdOffset;
        for (var i = 0; i < count; i++) {
          if (view.getUint32(pos, true) !== 0x02014b50) { break; }
          var method = view.getUint16(pos + 10, true);
          var compSize = view.getUint32(pos + 20, true);
          var nameLen = view.getUint16(pos + 28, true);
          var extraLen = view.getUint16(pos + 30, true);
          var commentLen = view.getUint16(pos + 32, true);
          var localOffset = view.getUint32(pos + 42, true);
          var name = new TextDecoder().decode(new Uint8Array(buf, pos + 46, nameLen));
          entries.push({ name: name, method: method, compSize: compSize, localOffset: localOffset });
          pos += 46 + nameLen + extraLen + commentLen;
        }
        // Giải nén tuần tự từng entry.
        var chain = Promise.resolve({});
        entries.forEach(function (en) {
          chain = chain.then(function (out) {
            var lo = en.localOffset;
            if (view.getUint32(lo, true) !== 0x04034b50) { return out; }
            var nl = view.getUint16(lo + 26, true);
            var el = view.getUint16(lo + 28, true);
            var dataStart = lo + 30 + nl + el;
            var raw = new Uint8Array(buf, dataStart, en.compSize);
            if (en.method === 0) {
              out[en.name] = raw.slice().buffer;
              return out;
            }
            if (en.method === 8) {
              var ds = new DecompressionStream('deflate-raw');
              var writer = ds.writable.getWriter();
              var reader = ds.readable.getReader();
              writer.write(raw);
              writer.close();
              var chunks = [];
              var readAll = function () {
                return reader.read().then(function (r) {
                  if (r.done) { return out; }
                  chunks.push(r.value);
                  return readAll();
                });
              };
              return readAll().then(function () {
                var total = chunks.reduce(function (a, c) { return a + c.length; }, 0);
                var merged = new Uint8Array(total);
                var off = 0;
                chunks.forEach(function (c) { merged.set(c, off); off += c.length; });
                out[en.name] = merged.buffer;
                return out;
              });
            }
            return out; // phương thức nén khác: bỏ qua entry này
          });
        });
        return chain;
      });
    };
  }

  function parseSrtTime(s) {
    var m = s.trim().match(/(\d+):(\d+):(\d+)[,.](\d+)/);
    if (!m) { return null; }
    return (+m[1]) * 3600 + (+m[2]) * 60 + (+m[3]) + (+m[4]) / 1000;
  }

  function fmtTime(sec) {
    var h = Math.floor(sec / 3600);
    var m = Math.floor((sec % 3600) / 60);
    var s = sec % 60;
    return ('0' + h).slice(-2) + ':' + ('0' + m).slice(-2) + ':' + s.toFixed(3).padStart(6, '0');
  }

  function parseSrtText(text) {
    var cues = [];
    var blocks = text.replace(/\r\n/g, '\n').split(/\n\s*\n/);
    blocks.forEach(function (block) {
      var lines = block.split('\n').filter(function (l) { return l.trim() !== ''; });
      if (!lines.length) { return; }
      var timeLine = lines.find(function (l) { return l.indexOf('-->') >= 0; });
      if (!timeLine) { return; }
      var parts = timeLine.split('-->');
      var start = parseSrtTime(parts[0]);
      var end = parseSrtTime(parts[1] || '');
      if (start == null || end == null) { return; }
      var textLines = lines.slice(lines.indexOf(timeLine) + 1)
        .map(function (l) { return l.replace(/<[^>]+>/g, '').replace(/\{[^}]*\}/g, ''); });
      cues.push({ start: start, end: end, text: textLines.join(' ') });
    });
    return cues;
  }

  function render(el) {
    el.innerHTML =
      '<h2>Lồng tiếng .srt</h2>'
      + '<p class="hp-hint">Quy tắc lồng tiếng: câu dài được đọc nhanh tối đa <strong>1,5×</strong>, '
      + 'chưa vừa thì lấn khoảng lặng sau rồi đẩy câu sau lùi — <strong>không bao giờ cắt chữ</strong>. '
      + 'Audio kết quả dài đúng bằng video; câu nào bị lùi sẽ có trong danh sách bên dưới kèm file SRT đã chỉnh mốc.</p>'
      + '<div id="srt-drop" class="hp-drop">Kéo thả file .srt/.vtt vào đây, hoặc '
      + '<label class="hp-file-label">chọn file <input id="srt-file" type="file" accept=".srt,.vtt"></label></div>'
      + '<div class="hp-row"><label>Giọng <select id="srt-voice"></select></label>'
      + '<label>Tốc độ <input id="srt-speed" type="number" min="0.75" max="1.5" step="0.05" value="1.0"> × (0,75–1,5)</label>'
      + '<button id="srt-dub" type="button" disabled>Lồng tiếng</button></div>'
      + '<p id="srt-progress" role="status"></p>'
      + '<h3>Danh sách câu + mốc giờ</h3>'
      + '<div id="srt-cues"><p>Chưa có file phụ đề.</p></div>'
      + '<h3>Câu bị lùi (nếu có)</h3>'
      + '<div id="srt-delayed"><p>Chưa lồng tiếng.</p></div>'
      + '<div class="hp-row"><button id="srt-play" type="button" disabled>Nghe lại audio</button>'
      + '<button id="srt-download-zip" type="button" disabled>Tải ZIP (WAV + SRT đã chỉnh + báo cáo)</button></div>'
      + '<p id="srt-status" role="status"></p>';

    var cuesEl = el.querySelector('#srt-cues');
    var delayedEl = el.querySelector('#srt-delayed');
    var progressEl = el.querySelector('#srt-progress');
    var statusEl = el.querySelector('#srt-status');
    var dubBtn = el.querySelector('#srt-dub');
    var playBtn = el.querySelector('#srt-play');
    var zipBtn = el.querySelector('#srt-download-zip');
    var fileInput = el.querySelector('#srt-file');
    var dropEl = el.querySelector('#srt-drop');

    var cues = [];
    var fileName = '';
    var zipBlob = null;
    var audioBlob = null;
    var audioUrl = null;

    function setStatus(msg, isErr) {
      statusEl.textContent = msg || '';
      statusEl.style.color = isErr ? '#b00020' : '';
    }

    function drawCues(activeIndex) {
      if (!cues.length) { cuesEl.innerHTML = '<p>Chưa có file phụ đề.</p>'; return; }
      cuesEl.innerHTML = '<table class="hp-table"><thead><tr><th>#</th><th>Bắt đầu</th><th>Kết thúc</th><th>Câu</th><th>Tiến trình</th></tr></thead><tbody>'
        + cues.map(function (c, i) {
          var state = '';
          if (activeIndex != null) {
            state = i < activeIndex ? '✓ Xong' : (i === activeIndex ? '… Đang lồng' : 'Chờ');
          }
          return '<tr><td>' + (i + 1) + '</td><td>' + fmtTime(c.start) + '</td><td>' + fmtTime(c.end) + '</td>'
            + '<td>' + esc(c.text) + '</td><td>' + state + '</td></tr>';
        }).join('') + '</tbody></table>';
    }

    function loadSubtitleFile(file) {
      if (!file) { return; }
      if (!/\.(srt|vtt)$/i.test(file.name)) {
        setStatus('Chỉ nhận file .srt/.vtt.', true); return;
      }
      fileName = file.name;
      var reader = new FileReader();
      reader.onload = function () {
        cues = parseSrtText(String(reader.result));
        if (!cues.length) { setStatus('Không đọc được câu nào trong file "' + fileName + '".', true); return; }
        drawCues(null);
        dubBtn.disabled = false;
        setStatus('Đã đọc ' + cues.length + ' câu từ "' + fileName + '" (' + fmtTime(cues[0].start)
          + ' → ' + fmtTime(cues[cues.length - 1].end) + '). Chọn giọng + tốc độ rồi bấm Lồng tiếng.');
      };
      reader.readAsText(file);
    }

    fileInput.addEventListener('change', function (e) { loadSubtitleFile(e.target.files[0]); });
    ['dragover', 'dragenter'].forEach(function (evt) {
      dropEl.addEventListener(evt, function (e) { e.preventDefault(); dropEl.classList.add('hp-drop-over'); });
    });
    ['dragleave', 'drop'].forEach(function (evt) {
      dropEl.addEventListener(evt, function (e) { e.preventDefault(); dropEl.classList.remove('hp-drop-over'); });
    });
    dropEl.addEventListener('drop', function (e) {
      var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      loadSubtitleFile(f);
    });

    // Nạp danh sách giọng.
    hpFetch('/voices?engine=v3').then(function (resp) { return resp.ok ? resp.json() : []; })
      .then(function (list) {
        var sel = el.querySelector('#srt-voice');
        sel.innerHTML = (Array.isArray(list) ? list : []).map(function (v) {
          return '<option value="' + esc(v.id) + '"' + (v.id === 'Hải Đăng' ? ' selected' : '') + '>'
            + esc(v.name || v.id) + '</option>';
        }).join('');
      }).catch(function () { /* để trống, server sẽ báo lỗi rõ khi gửi */ });

    dubBtn.addEventListener('click', function () {
      if (!cues.length) { setStatus('Chưa có file phụ đề.', true); return; }
      var voice = el.querySelector('#srt-voice').value || 'Hải Đăng';
      var speed = parseFloat(el.querySelector('#srt-speed').value) || 1.0;
      if (speed < 0.75 || speed > MAX_RATE) {
        setStatus('Tốc độ chỉ trong khoảng 0,75×–1,5×.', true); return;
      }
      var form = new FormData();
      form.append('file', new Blob([cues.map(function (c, i) {
        return (i + 1) + '\n' + fmtTime(c.start).replace('.', ',') + ' --> '
          + fmtTime(c.end).replace('.', ',') + '\n' + c.text + '\n';
      }).join('\n')], { type: 'text/plain' }), fileName || 'phu-de.srt');
      form.append('voice_id', voice);
      form.append('speed', String(speed));
      dubBtn.disabled = true;
      progressEl.textContent = 'Đang lồng tiếng ' + cues.length + ' câu… (POST /api/tts/srt-dub)';
      drawCues(0);
      // Tiến trình từng câu: server chạy đồng bộ trong 1 request nên UI hiển
      // thị trạng thái chung trong lúc chờ; danh sách câu được đánh dấu xong
      // hết khi ZIP về, kèm bảng câu bị lùi từ report.json.
      hpFetch('/api/tts/srt-dub', { method: 'POST', body: form })
        .then(function (resp) {
          if (!resp.ok) { return resp.text().then(function (t) { throw new Error('API trả ' + resp.status + ': ' + t); }); }
          return resp.blob();
        })
        .then(function (blob) {
          zipBlob = blob;
          zipBtn.disabled = false;
          return NS.readZip(blob).then(function (entries) {
            var report = null;
            if (entries['report.json']) {
              report = JSON.parse(new TextDecoder().decode(entries['report.json']));
            }
            if (entries['dub.wav']) {
              audioBlob = new Blob([entries['dub.wav']], { type: 'audio/wav' });
              if (audioUrl) { URL.revokeObjectURL(audioUrl); }
              audioUrl = URL.createObjectURL(audioBlob);
              playBtn.disabled = false;
            }
            drawCues(cues.length); // tất cả đã xong
            var delayed = (report && report.delayed) || [];
            if (delayed.length) {
              delayedEl.innerHTML = '<table class="hp-table"><thead><tr><th>Câu</th><th>Mốc gốc</th>'
                + '<th>Mốc mới</th><th>Lùi (giây)</th><th>Tốc độ thực</th></tr></thead><tbody>'
                + delayed.map(function (d) {
                  return '<tr><td>' + (d.index + 1) + '</td><td>' + d.scheduled_start_s.toFixed(3) + ' s</td>'
                    + '<td>' + d.actual_start_s.toFixed(3) + ' s</td><td>+' + d.shift_s.toFixed(3) + ' s</td>'
                    + '<td>' + d.effective_rate + '×</td></tr>';
                }).join('') + '</tbody></table>'
                + '<p>File dub.srt trong ZIP đã chỉnh mốc theo các câu bị lùi.</p>';
            } else {
              delayedEl.innerHTML = '<p>Không có câu nào bị lùi — mọi câu đều khớp mốc gốc.</p>';
            }
            var dur = report ? report.duration_s : null;
            progressEl.textContent = 'Đã lồng xong ' + cues.length + ' câu'
              + (dur != null ? ', audio dài ' + dur.toFixed(2) + ' s (đúng bằng video).' : '.')
              + (delayed.length ? ' Có ' + delayed.length + ' câu bị lùi (xem bảng).' : '');
            setStatus('Đã lồng tiếng xong. Tải ZIP để lấy WAV + SRT đã chỉnh mốc + report.json.');
          });
        })
        .catch(function (e) {
          drawCues(null);
          setStatus('Không lồng được tiếng: ' + e.message, true);
        })
        .finally(function () { dubBtn.disabled = false; });
    });

    playBtn.addEventListener('click', function () {
      if (audioUrl && NS.player) { NS.player.play(audioUrl, 'Lồng tiếng SRT'); }
    });

    zipBtn.addEventListener('click', function () {
      if (!zipBlob) { return; }
      var url = URL.createObjectURL(zipBlob);
      var a = document.createElement('a');
      a.href = url; a.download = 'srt-dub.zip'; a.click();
      setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
    });

    drawCues(null);
  }

  registerTab({ id: 'srt', group: 'Tạo', label: 'Lồng tiếng .srt', render: render });
})();
