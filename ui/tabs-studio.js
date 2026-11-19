/* HP Voice Studio — Tab Phòng thu / TTS Studio (TK3.1, test T3.1, SPEC §5).
 *
 * - Ô nhập text + đếm ký tự (giới hạn 20.000, SPEC §4/Y6).
 * - Dropdown Giọng đọc (25 preset + clone, ghi giới tính/vùng/phong cách),
 *   nghe thử từng giọng qua PreviewCache (GET /voices/{id}/preview, Y7).
 * - Chọn Engine V3/V4 — V4 luôn hiện phí/ký tự trước khi gửi (TK3.6).
 * - Tốc độ 0,75×–1,5×; chèn cảm xúc [cười]/[thở dài]/[hắng giọng] + thẻ nghỉ
 *   [nghỉ 2s]/[nghỉ 500ms]; nút Từ điển (API /api/dict).
 * - Nút Tạo -> POST /api/tts/generate (200 audio hoặc 202 job xếp hàng);
 *   tạo kèm .srt -> POST /api/tts/generate-with-subtitles (ZIP).
 * - Xuất WAV/MP3: MP3 qua FFmpeg tải sau (Q21) — server báo không có FFmpeg
 *   thì chỉ WAV + báo rõ lý do (không crash).
 * - Nghe lại CHỈ qua window.HPVoiceStudio.player (singleton, TK3.7) —
 *   file này không tự tạo thẻ Audio mới.
 */
(function () {
  'use strict';

  var NS = window.HPVoiceStudio = window.HPVoiceStudio || {};
  var API_BASE = 'http://127.0.0.1:8124';
  var MAX_CHARS = 20000;

  function api() { return NS.api || null; }

  function toast(msg, kind) {
    if (typeof NS.toast === 'function') { NS.toast(msg, kind); }
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>\"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function hpFetch(path, opts) {
    if (api() && typeof api().fetchJson === 'function') { return api().fetchJson(path, opts); }
    if (api() && typeof api().request === 'function') { return api().request(path, opts); }
    return fetch(API_BASE + path, opts);
  }

  function hpFetchRaw(path, opts) {
    if (api() && typeof api().requestRaw === 'function') { return api().requestRaw(path, opts); }
    return fetch(API_BASE + path, opts);
  }

  function playBlob(blob, label) {
    var player = NS.player;
    if (!player || typeof player.playBlob !== 'function') {
      toast('Trình phát chưa sẵn sàng (file ui/player.js chưa nạp) — bấm nút '
        + 'Tải về để nghe file thay vì phát trực tiếp.', 'error');
      return false;
    }
    player.playBlob(blob, label);
    return true;
  }

  function registerTab(def) {
    if (typeof NS.registerTab === 'function') { NS.registerTab(def); return; }
    (NS._pendingTabs = NS._pendingTabs || []).push(def);
  }

  function render(el) {
    var state = {
      voices: [],
      busy: false,
      pollTimers: {},
      lastBlobUrl: null,
      lastBlob: null,
      lastLabel: ''
    };

    el.innerHTML =
      '<h2>Phòng thu</h2>'
      + '<p class="hp-hint">Nhập text, chọn giọng, bấm Tạo — nghe lại ngay bên dưới. '
      + 'V4 tính phí theo ký tự, xem ước tính phí trước khi gửi.</p>'
      + '<label for="studio-text">Nội dung đọc</label>'
      + '<textarea id="studio-text" rows="6" maxlength="20000" '
      + 'placeholder="Nhập text cần đọc thành giọng nói..."></textarea>'
      + '<p id="studio-char-count" role="status">0 / 20.000 ký tự</p>'
      + '<div class="hp-row"><label>Giọng đọc '
      + '<select id="studio-voice"><option value="">— Đang tải giọng... —</option></select></label>'
      + '<button id="studio-voice-preview" type="button">Nghe thử giọng</button></div>'
      + '<p id="studio-preview-cost" role="status"></p>'
      + '<div class="hp-row"><label>Engine '
      + '<select id="studio-engine">'
      + '<option value="v3">V3 local (miễn phí)</option>'
      + '<option value="v4">V4 cloud (tính phí theo ký tự)</option>'
      + '</select></label>'
      + '<label>Tốc độ <input id="studio-speed" type="range" min="0.75" max="1.5" '
      + 'step="0.05" value="1"> <span id="studio-speed-value">1,00×</span></label>'
      + '<label>Định dạng <select id="studio-format">'
      + '<option value="wav">WAV</option><option value="mp3">MP3 (cần FFmpeg)</option>'
      + '</select></label></div>'
      + '<p id="studio-v4-fee" role="status"></p>'
      + '<div class="hp-row" role="group" aria-label="Chèn cảm xúc và thẻ nghỉ">'
      + '<button id="studio-insert-laugh" type="button">[cười]</button>'
      + '<button id="studio-insert-sigh" type="button">[thở dài]</button>'
      + '<button id="studio-insert-throat" type="button">[hắng giọng]</button>'
      + '<button id="studio-insert-pause-2s" type="button">[nghỉ 2s]</button>'
      + '<button id="studio-insert-pause-500ms" type="button">[nghỉ 500ms]</button>'
      + '<button id="studio-dict-btn" type="button">Từ điển</button></div>'
      + '<div id="studio-dict-panel" class="hp-panel" hidden>'
      + '<h3>Từ điển phát âm (API /api/dict)</h3>'
      + '<div class="hp-row"><input id="studio-dict-word" placeholder="Từ (VD: VieNeu)">'
      + '<input id="studio-dict-reading" placeholder="Cách đọc (VD: vi-niu)">'
      + '<button id="studio-dict-add" type="button">Thêm</button></div>'
      + '<div id="studio-dict-list"></div>'
      + '<p id="studio-dict-note" class="hp-hint"></p></div>'
      + '<div class="hp-row"><label><input id="studio-with-srt" type="checkbox"> '
      + 'Tạo kèm file .srt (mốc từng câu)</label>'
      + '<button id="studio-create-btn" type="button" class="hp-cta">Tạo</button>'
      + '<button id="studio-stop-btn" type="button">Dừng phát</button></div>'
      + '<p id="studio-status" role="status"></p>'
      + '<div id="studio-result" class="hp-row" hidden>'
      + '<button id="studio-play-btn" type="button">Nghe lại</button>'
      + '<a id="studio-download" href="#" download>Tải về</a></div>'
      + '<h3>Hàng đợi</h3>'
      + '<p class="hp-hint">Nhiều bản đọc xếp hàng: bản sau chờ bản trước xong '
      + '(tối đa 20 job chờ, TTL 60 phút).</p>'
      + '<div id="studio-queue"></div>';

    var textEl = el.querySelector('#studio-text');
    var countEl = el.querySelector('#studio-char-count');
    var voiceEl = el.querySelector('#studio-voice');
    var previewBtn = el.querySelector('#studio-voice-preview');
    var previewCostEl = el.querySelector('#studio-preview-cost');
    var engineEl = el.querySelector('#studio-engine');
    var speedEl = el.querySelector('#studio-speed');
    var speedValEl = el.querySelector('#studio-speed-value');
    var formatEl = el.querySelector('#studio-format');
    var v4FeeEl = el.querySelector('#studio-v4-fee');
    var srtEl = el.querySelector('#studio-with-srt');
    var createBtn = el.querySelector('#studio-create-btn');
    var stopBtn = el.querySelector('#studio-stop-btn');
    var statusEl = el.querySelector('#studio-status');
    var resultEl = el.querySelector('#studio-result');
    var playBtn = el.querySelector('#studio-play-btn');
    var downloadEl = el.querySelector('#studio-download');
    var queueEl = el.querySelector('#studio-queue');
    var dictPanel = el.querySelector('#studio-dict-panel');

    function setStatus(msg, isErr) {
      statusEl.textContent = msg || '';
      statusEl.className = isErr ? 'hp-error' : '';
    }

    function updateCount() {
      var n = textEl.value.length;
      countEl.textContent = n.toLocaleString('vi-VN') + ' / 20.000 ký tự';
      countEl.className = n > MAX_CHARS ? 'hp-error' : '';
      updateV4Fee();
    }

    /** Ước tính phí V4 hiện TRƯỚC khi gửi (TK3.6). */
    function updateV4Fee() {
      if (engineEl.value !== 'v4') {
        v4FeeEl.textContent = 'Engine V3 local: miễn phí, chạy offline sau lần tải model đầu.';
        previewCostEl.textContent = '';
        return;
      }
      var est = api() ? api().estimateV4Cost(textEl.value)
        : { chars: textEl.value.length,
            billable: Math.max(50, textEl.value.length),
            tokens: Math.max(50, textEl.value.length) * 3.4 };
      var note = 'V4 tính phí theo ký tự: ' + est.chars + ' ký tự (tính tối thiểu '
        + '50/request) × 3,4 ≈ ' + Math.round(est.tokens) + ' token.';
      if (textEl.value.indexOf('[nghỉ') !== -1) {
        note += ' Cảnh báo: text có thẻ [nghỉ] sẽ bị V4 tách thành nhiều đoạn, '
          + 'mỗi đoạn tính tối thiểu 50 ký tự nên phí có thể nhân lên — xem docs/v4-billing.md.';
      }
      v4FeeEl.textContent = note + ' Hệ số 3,4 là ví dụ trong OpenAPI — số thật '
        + 'lấy từ GET /v1/engines khi có key.';
    }

    function insertTag(tag) {
      var start = textEl.selectionStart || 0;
      var end = textEl.selectionEnd || 0;
      textEl.value = textEl.value.slice(0, start) + tag + textEl.value.slice(end);
      textEl.focus();
      textEl.selectionStart = textEl.selectionEnd = start + tag.length;
      updateCount();
    }

    function loadVoices() {
      hpFetch('/voices').then(function (voices) {
        state.voices = voices || [];
        var presets = state.voices.filter(function (v) { return !v.is_clone; });
        var clones = state.voices.filter(function (v) { return v.is_clone; });
        function opt(v) {
          var meta = [v.gender, v.region, v.style].filter(Boolean).join(' · ');
          return '<option value="' + esc(v.id) + '">' + esc(v.name)
            + (meta ? ' — ' + esc(meta) : '') + '</option>';
        }
        var html = '<optgroup label="Giọng preset (V3)">' + presets.map(opt).join('') + '</optgroup>';
        if (clones.length) {
          html += '<optgroup label="Giọng của tôi (clone)">' + clones.map(opt).join('') + '</optgroup>';
        }
        voiceEl.innerHTML = html || '<option value="">— Không có giọng nào —</option>';
        return hpFetch('/api/config').catch(function () { return {}; });
      }).then(function (cfg) {
        var def = (cfg && cfg.audio && cfg.audio.default_voice) || 'Hải Đăng';
        if (voiceEl.querySelector('option[value="' + def + '"]')) { voiceEl.value = def; }
        if (cfg && cfg.engine && cfg.engine.default) { engineEl.value = cfg.engine.default; }
        if (cfg && cfg.audio && cfg.audio.default_speed) {
          speedEl.value = cfg.audio.default_speed;
          speedValEl.textContent = Number(speedEl.value).toFixed(2).replace('.', ',') + '×';
        }
        updateV4Fee();
      }).catch(function (err) {
        voiceEl.innerHTML = '<option value="">— Không tải được giọng —</option>';
        setStatus('Không tải được danh sách giọng: ' + (err.message || err)
          + ' — kiểm tra server đã chạy ở 127.0.0.1:8124 chưa.', true);
      });
    }

    /** Nghe thử giọng qua PreviewCache (Y7): V3 gọi endpoint (lần 2 trả cache). */
    function previewVoice() {
      var voice = voiceEl.value;
      if (!voice) { toast('Chưa chọn giọng để nghe thử — chọn 1 giọng trong dropdown trước.', 'error'); return; }
      if (engineEl.value === 'v4') {
        var sample = 'Xin chào, đây là giọng đọc mẫu của HP Voice Studio.';
        var est = api() ? api().estimateV4Cost(sample) : { billable: 50, tokens: 170 };
        previewCostEl.textContent = 'Nghe thử V4: ước tính ' + est.billable
          + ' ký tự (tối thiểu 50/request) ≈ ' + Math.round(est.tokens)
          + ' token — V4 tính phí theo ký tự. Endpoint nghe thử trên server hiện '
          + 'chỉ có giọng V3 (GET /voices/{id}/preview); nghe thử V4 chờ API riêng, '
          + 'hiện chỉ nghe thử được giọng V3 — chuyển Engine về V3 để nghe thử.';
        toast('Nghe thử V4 chưa hỗ trợ trên server hiện tại (chỉ có giọng V3) — '
          + 'chuyển Engine về V3 để nghe thử, hoặc chờ endpoint preview V4.', 'error');
        return;
      }
      previewCostEl.textContent = 'Đang tạo mẫu nghe thử...';
      hpFetchRaw('/voices/' + encodeURIComponent(voice) + '/preview').then(function (resp) {
        if (!resp.ok) {
          return resp.text().then(function (t) {
            var msg = t;
            try { msg = JSON.parse(t).error.message; } catch (e) { /* giữ text */ }
            throw new Error(msg || ('Không nghe thử được giọng ' + voice));
          });
        }
        var cached = resp.headers.get('X-Cache') === 'HIT';
        previewCostEl.textContent = cached
          ? 'Đang phát mẫu đã lưu sẵn trong cache (không tổng hợp lại).'
          : 'Đang phát mẫu vừa tạo — đã lưu vào cache, lần sau nghe lại không cần tạo nữa.';
        return resp.blob();
      }).then(function (blob) {
        playBlob(blob, 'Nghe thử ' + voice);
      }).catch(function (err) {
        previewCostEl.textContent = '';
        toast('Không nghe thử được giọng ' + voice + ': ' + (err.message || err)
          + ' — thử chọn giọng khác hoặc kiểm tra server.', 'error');
      });
    }

    function addQueueItem(jobId, label) {
      var row = document.createElement('div');
      row.className = 'hp-queue-row';
      row.id = 'studio-queue-' + jobId;
      row.innerHTML = '<span>' + esc(label) + '</span> '
        + '<span class="hp-queue-status">Đang chờ...</span> '
        + '<button type="button" class="hp-queue-cancel">Hủy job</button>';
      queueEl.appendChild(row);
      row.querySelector('.hp-queue-cancel').addEventListener('click', function () {
        hpFetch('/api/jobs/' + encodeURIComponent(jobId) + '/cancel', { method: 'POST' })
          .then(function () { setQueueStatus(jobId, 'Đã hủy.'); })
          .catch(function (err) {
            toast('Không hủy được job ' + jobId + ': ' + (err.message || err)
              + ' — job có thể đã xong hoặc đã hủy trước đó.', 'error');
          });
      });
      return row;
    }

    function setQueueStatus(jobId, text) {
      var row = document.getElementById('studio-queue-' + jobId);
      if (row) {
        var st = row.querySelector('.hp-queue-status');
        if (st) { st.textContent = text; }
      }
    }

    function pollJob(jobId, label, isZip) {
      addQueueItem(jobId, label);
      var timer = setInterval(function () {
        hpFetch('/api/jobs/' + encodeURIComponent(jobId)).then(function (job) {
          if (job.status === 'done') {
            clearInterval(timer);
            delete state.pollTimers[jobId];
            setQueueStatus(jobId, 'Xong.');
            hpFetchRaw('/api/jobs/' + encodeURIComponent(jobId) + '/result').then(function (resp) {
              if (!resp.ok) { throw new Error('Không tải được kết quả job ' + jobId + '.'); }
              return resp.blob();
            }).then(function (blob) {
              showResult(blob, label, isZip);
              setStatus('Xong: ' + label);
            }).catch(function (err) {
              setStatus('Job xong nhưng không tải được kết quả: ' + (err.message || err)
                + ' — thử tải lại từ tab Bản đã tạo.', true);
            });
          } else if (job.status === 'error') {
            clearInterval(timer);
            delete state.pollTimers[jobId];
            setQueueStatus(jobId, 'Lỗi.');
            setStatus('Tạo thất bại: ' + (job.error || 'không rõ lý do')
              + ' — sửa text/giọng rồi bấm Tạo lại.', true);
          } else if (job.status === 'cancelled') {
            clearInterval(timer);
            delete state.pollTimers[jobId];
            setQueueStatus(jobId, 'Đã hủy.');
            setStatus('Job đã hủy.');
          } else {
            setQueueStatus(jobId, 'Đang ' + (job.status === 'running' ? 'tạo...' : 'chờ...')
              + (job.progress != null ? ' ' + Math.round(job.progress * 100) + '%' : ''));
          }
        }).catch(function (err) {
          clearInterval(timer);
          delete state.pollTimers[jobId];
          setQueueStatus(jobId, 'Lỗi poll.');
          setStatus('Không theo dõi được job ' + jobId + ': ' + (err.message || err)
            + ' — kiểm tra server rồi mở tab Bản đã tạo để xem kết quả.', true);
        });
      }, 1000);
      state.pollTimers[jobId] = timer;
    }

    function showResult(blob, label, isZip) {
      if (state.lastBlobUrl) {
        try { URL.revokeObjectURL(state.lastBlobUrl); } catch (e) { /* bỏ qua */ }
      }
      state.lastBlob = blob;
      state.lastBlobUrl = URL.createObjectURL(blob);
      state.lastLabel = label;
      resultEl.hidden = false;
      var ext = isZip ? 'zip' : (formatEl.value === 'mp3' ? 'mp3' : 'wav');
      downloadEl.href = state.lastBlobUrl;
      downloadEl.download = 'hp-voice-studio.' + ext;
      downloadEl.textContent = 'Tải về (.' + ext + ')';
      if (!isZip) { playBlob(blob, label); }
      else {
        toast('Đã tạo xong file ZIP (audio + .srt) — bấm Tải về để lưu.', 'info');
      }
    }

    function createAudio() {
      var text = textEl.value.trim();
      if (!text) {
        toast('Chưa nhập text — nhập nội dung cần đọc rồi bấm Tạo.', 'error');
        textEl.focus();
        return;
      }
      if (text.length > MAX_CHARS) {
        toast('Text dài ' + text.length + ' ký tự, vượt giới hạn 20.000 ký tự/request '
          + '— chia nhỏ text rồi tạo từng phần.', 'error');
        return;
      }
      var voice = voiceEl.value;
      if (!voice) {
        toast('Chưa chọn giọng đọc — chọn 1 giọng trong dropdown Giọng đọc trước.', 'error');
        return;
      }
      var engineName = engineEl.value;
      var speed = parseFloat(speedEl.value);
      if (speed < 0.75 || speed > 1.5) {
        toast('Tốc độ phải trong 0,75×–1,5×, nhận ' + speed + '×.', 'error');
        return;
      }
      var withSrt = srtEl.checked;
      var format = formatEl.value;
      var label = 'Bản đọc — ' + voice + ' (' + engineName.toUpperCase() + ', ' + speed + '×)';
      setStatus('Đang gửi yêu cầu tạo...');
      createBtn.disabled = true;
      // V4 chưa có key thì báo ngay, khỏi gửi request rồi mới lỗi (TK3.6).
      var keyCheck = (engineName === 'v4')
        ? hpFetch('/api/config').then(function (cfg) { return !!cfg.v4_configured; })
          .catch(function () { return true; })
        : Promise.resolve(true);
      keyCheck.then(function (hasKey) {
        if (!hasKey) {
          throw new Error('Chưa có key V4 — nhập key ở tab Cài đặt → Engine V4, '
            + 'hoặc chuyển Engine về V3 local (miễn phí) rồi bấm Tạo lại.');
        }
        var path = withSrt ? '/api/tts/generate-with-subtitles' : '/api/tts/generate';
        return hpFetchRaw(path, {
          method: 'POST',
          body: JSON.stringify({
            text: text, voice_id: voice, engine: engineName,
            speed: speed, format: format
          })
        });
      }).then(function (resp) {
        if (resp.status === 202) {
          return resp.json().then(function (data) {
            setStatus('CPU đang bận — bản đọc đã xếp hàng (job ' + data.job_id + ').');
            pollJob(data.job_id, label, withSrt);
          });
        }
        if (!resp.ok) {
          return resp.text().then(function (t) {
            var msg = t;
            try { msg = JSON.parse(t).error.message; } catch (e) { /* giữ text */ }
            throw new Error(msg || ('Tạo thất bại (HTTP ' + resp.status + ')'));
          });
        }
        return resp.blob().then(function (blob) {
          setStatus('Xong: ' + label);
          showResult(blob, label, withSrt);
        });
      }).catch(function (err) {
        var msg = err.message || String(err);
        if (msg.indexOf('FFmpeg') !== -1) {
          msg += ' — muốn xuất MP3 hãy cài FFmpeg hệ thống hoặc để app tải FFmpeg '
            + 'về lần đầu chạy (cần mạng); trước mắt chọn định dạng WAV để tạo ngay.';
        }
        setStatus(msg, true);
        toast(msg, 'error');
      }).then(function () { createBtn.disabled = false; });
    }

    function loadDict() {
      var listEl = el.querySelector('#studio-dict-list');
      var noteEl = el.querySelector('#studio-dict-note');
      hpFetch('/api/dict').then(function (data) {
        var items = (data && data.items) || [];
        listEl.innerHTML = items.length
          ? items.map(function (it) {
              return '<div>' + esc(it.word) + ' → ' + esc(it.reading) + '</div>';
            }).join('')
          : '<p class="hp-hint">Từ điển đang trống.</p>';
        noteEl.textContent = 'Từ điển áp dụng trước khi tạo giọng (tối đa 2.000 mục).';
      }).catch(function (err) {
        listEl.innerHTML = '';
        noteEl.textContent = 'Không gọi được API từ điển — chờ API từ điển '
          + '(máy chủ chưa trả lời: ' + (err.message || err) + '). Vẫn nhập tay '
          + 'ở trên và bấm Thêm khi API chạy lại.';
      });
    }

    textEl.addEventListener('input', updateCount);
    engineEl.addEventListener('change', updateV4Fee);
    speedEl.addEventListener('input', function () {
      speedValEl.textContent = Number(speedEl.value).toFixed(2).replace('.', ',') + '×';
    });
    previewBtn.addEventListener('click', previewVoice);
    createBtn.addEventListener('click', createAudio);
    stopBtn.addEventListener('click', function () {
      if (NS.player && typeof NS.player.stop === 'function') { NS.player.stop(); }
      Object.keys(state.pollTimers).forEach(function (jobId) {
        clearInterval(state.pollTimers[jobId]);
        delete state.pollTimers[jobId];
      });
      setStatus('Đã dừng phát.');
    });
    playBtn.addEventListener('click', function () {
      if (state.lastBlob) { playBlob(state.lastBlob, state.lastLabel); }
      else { toast('Chưa có bản đọc nào để nghe lại — bấm Tạo trước.', 'error'); }
    });
    el.querySelector('#studio-insert-laugh').addEventListener('click', function () { insertTag('[cười]'); });
    el.querySelector('#studio-insert-sigh').addEventListener('click', function () { insertTag('[thở dài]'); });
    el.querySelector('#studio-insert-throat').addEventListener('click', function () { insertTag('[hắng giọng]'); });
    el.querySelector('#studio-insert-pause-2s').addEventListener('click', function () { insertTag('[nghỉ 2s]'); });
    el.querySelector('#studio-insert-pause-500ms').addEventListener('click', function () { insertTag('[nghỉ 500ms]'); });
    el.querySelector('#studio-dict-btn').addEventListener('click', function () {
      dictPanel.hidden = !dictPanel.hidden;
      if (!dictPanel.hidden) { loadDict(); }
    });
    el.querySelector('#studio-dict-add').addEventListener('click', function () {
      var word = el.querySelector('#studio-dict-word').value.trim();
      var reading = el.querySelector('#studio-dict-reading').value.trim();
      if (!word || !reading) {
        toast('Nhập cả từ và cách đọc rồi mới bấm Thêm.', 'error');
        return;
      }
      hpFetch('/api/dict', { method: 'POST', body: JSON.stringify({ word: word, reading: reading }) })
        .then(function () { loadDict(); })
        .catch(function (err) {
          toast('Không thêm được từ vào từ điển: ' + (err.message || err)
            + ' — kiểm tra server rồi thử lại.', 'error');
        });
    });

    updateCount();
    loadVoices();
  }

  registerTab({ id: 'studio', group: 'Tạo', label: 'Phòng thu', render: render });
})();
