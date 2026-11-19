/* HP Voice Studio — Tab Cài đặt (TK3.5, test T3.7, SPEC §5).
 *
 * - Giọng mặc định; model (precision fp32/int8 + tự phát hiện CPU, threads).
 * - Thư mục lưu + thư mục model/cache.
 * - Engine V4: nhập/xoá key qua POST /api/config/v4-key — key lưu qua keyring,
 *   KHÔNG log, KHÔNG hiện lại key (chỉ trạng thái chưa có key / đã có key /
 *   lỗi); ước tính phí; ngưỡng cảnh báo ký tự.
 * - API local: cổng, bật/tắt LAN, nút tạo khoá mới.
 * - Giao diện sáng/tối; giới thiệu + giấy phép + ghi công VieNeu-TTS.
 * - Tab này không phát audio (không tự tạo thẻ Audio).
 *
 * LƯU Ý trung thực: server hiện chưa có endpoint kiểm tra số dư V4
 * (GET /v1/balance) hay đọc thông tin CPU, nên trạng thái "key hợp lệ" và
 * chi tiết CPU chỉ kiểm được khi có endpoint — tab ghi rõ điều đó thay vì
 * hiện số bịa (xem "chờ kiểm chứng thật" trong báo cáo TK3.1).
 */
(function () {
  'use strict';

  var NS = window.HPVoiceStudio = window.HPVoiceStudio || {};
  var API_BASE = 'http://127.0.0.1:8124';

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

  function registerTab(def) {
    if (typeof NS.registerTab === 'function') { NS.registerTab(def); return; }
    (NS._pendingTabs = NS._pendingTabs || []).push(def);
  }

  /** Key ngẫu nhiên cho LAN (chỉ hiển thị để sao chép — v1 chưa có endpoint lưu key LAN). */
  function randomKey() {
    var chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789';
    var out = '';
    var buf = new Uint32Array(32);
    if (window.crypto && window.crypto.getRandomValues) {
      window.crypto.getRandomValues(buf);
      for (var i = 0; i < 32; i++) { out += chars[buf[i] % chars.length]; }
    } else {
      for (var j = 0; j < 32; j++) { out += chars[Math.floor(Math.random() * chars.length)]; }
    }
    return out;
  }

  function render(el) {
    el.innerHTML =
      '<h2>Cài đặt</h2>'
      + '<p class="hp-hint">Cài đặt lưu bền vào config.yaml — khởi động lại app vẫn giữ (T3.7). '
      + 'Key V4 không bao giờ hiện lại hay ghi log.</p>'
      + '<p id="settings-status" role="status"></p>'
      + '<h3>Giọng đọc mặc định</h3>'
      + '<div class="hp-row"><label>Giọng mặc định '
      + '<select id="settings-default-voice"><option value="">— Đang tải giọng... —</option></select></label>'
      + '<label>Tốc độ mặc định <input id="settings-default-speed" type="number" '
      + 'min="0.75" max="1.5" step="0.05" value="1"></label></div>'
      + '<h3>Model V3 (local)</h3>'
      + '<div class="hp-row"><label>Precision '
      + '<select id="settings-precision">'
      + '<option value="auto">Tự động (theo CPU)</option>'
      + '<option value="fp32">fp32 (chậm hơn, không méo tiếng)</option>'
      + '<option value="int8">int8 (nhanh hơn, cần CPU có VNNI)</option>'
      + '</select></label>'
      + '<label>Threads <input id="settings-threads" type="number" min="0" max="16" step="1" value="0"></label></div>'
      + '<p id="settings-cpu-info" class="hp-hint">Tự phát hiện CPU: có VNNI (AVX-512 VNNI '
      + 'hoặc AVX-VNNI) thì precision tự động chọn int8, không có thì fp32 — mặc định '
      + 'an toàn là fp32. Chi tiết CPU của máy này (tên CPU, có/không VNNI) chỉ đọc '
      + 'được khi server có endpoint riêng — hiện chưa có, xem trong log khởi động server.</p>'
      + '<h3>Thư mục lưu</h3>'
      + '<div class="hp-row"><label>Thư mục lưu bản đã tạo '
      + '<input id="settings-output-dir" type="text" placeholder="Trống = thư mục mặc định theo OS"></label></div>'
      + '<div class="hp-row"><label>Thư mục model/cache '
      + '<input id="settings-model-dir" type="text" placeholder="Trống = cache Hugging Face mặc định"></label></div>'
      + '<div class="hp-row"><label>Thư mục lịch sử '
      + '<input id="settings-history-dir" type="text" placeholder="Trống = &lt;thư mục dữ liệu&gt;/history"></label></div>'
      + '<h3>FFmpeg (để xuất MP3)</h3>'
      + '<p id="settings-ffmpeg-status" role="status">Đang kiểm tra FFmpeg...</p>'
      + '<div class="hp-row"><button id="settings-ffmpeg-download" type="button">Tải FFmpeg</button>'
      + '<progress id="settings-ffmpeg-progress" max="100" value="0" style="display:none"></progress>'
      + '<span id="settings-ffmpeg-percent" class="hp-mono"></span></div>'
      + '<p id="settings-ffmpeg-hint" class="hp-hint">Chưa có FFmpeg thì chỉ xuất được '
      + 'WAV. Bấm "Tải FFmpeg" để tải bản LGPL (BtbN) về lần đầu — cần mạng, ~137 MB '
      + 'trên Linux / ~172 MB trên Windows, có resume + kiểm checksum. Có FFmpeg hệ '
      + 'thống thì app dùng luôn, không cần tải. Nếu tải lỗi vì mất mạng: kiểm tra mạng '
      + 'rồi bấm tải lại, hoặc cài FFmpeg hệ thống.</p>'
      + '<h3>Engine V4 (cloud, tính phí theo ký tự)</h3>'
      + '<p id="settings-v4-status" role="status">Chưa có key.</p>'
      + '<div class="hp-row"><label>Key V4 '
      + '<input id="settings-v4-key" type="password" autocomplete="off" '
      + 'placeholder="vn_sk_... (nhập key mới để đổi, để trống để xoá)"></label>'
      + '<button id="settings-v4-save" type="button">Lưu key</button>'
      + '<button id="settings-v4-clear" type="button">Xoá key</button></div>'
      + '<p id="settings-v4-estimate" class="hp-hint"></p>'
      + '<div class="hp-row"><label>Ngưỡng cảnh báo ký tự/phiên '
      + '<input id="settings-warn-chars" type="number" min="0" step="1000" value="100000"></label></div>'
      + '<h3>API local</h3>'
      + '<div class="hp-row"><label>Cổng API '
      + '<input id="settings-server-port" type="number" min="1" max="65535" step="1" value="8124"></label>'
      + '<label><input id="settings-lan-enabled" type="checkbox"> Bật LAN (cho máy khác gọi API)</label></div>'
      + '<p class="hp-hint">API mặc định chỉ bind 127.0.0.1. Bật LAN ở v1 không bắt buộc '
      + 'key (quyết định local-only) — chỉ bật LAN khi cần và trong mạng tin cậy.</p>'
      + '<div class="hp-row"><button id="settings-generate-lan-key" type="button">Tạo khoá LAN mới</button>'
      + '<span id="settings-lan-key-value" class="hp-mono"></span></div>'
      + '<p class="hp-hint">Khoá LAN tạo ở đây chỉ hiển thị để sao chép — server v1 chưa có '
      + 'endpoint lưu key LAN, nên khoá này chưa được server áp dụng (chờ endpoint riêng).</p>'
      + '<h3>Giao diện</h3>'
      + '<div class="hp-row"><label>Giao diện '
      + '<select id="settings-theme"><option value="light">Sáng</option>'
      + '<option value="dark">Tối</option></select></label></div>'
      + '<div class="hp-row"><button id="settings-save-btn" type="button" class="hp-cta">Lưu cài đặt</button></div>'
      + '<h3>Giới thiệu</h3>'
      + '<div id="settings-about">'
      + '<p>HP Voice Studio — studio tạo giọng đọc tiếng Việt chạy local, dùng cá nhân. '
      + 'Engine V3 local: VieNeu-TTS v3 Turbo (miễn phí, chạy offline sau lần tải model đầu). '
      + 'Engine V4 cloud (tùy chọn, tính phí theo ký tự) qua API chính thức của VieNeu.</p>'
      + '<p>Giấy phép: HP Voice Studio — Apache 2.0. Ghi công: VieNeu-TTS của '
      + 'pnnbao-ump (Apache 2.0) — xem NOTICE. Giọng preset V3 theo model card '
      + 'VieNeu-TTS v3 Turbo (Apache 2.0). FFmpeg tải về lần đầu chạy (BtbN) theo LGPL v3 — xem NOTICE.</p>'
      + '<p>Lưu ý pháp lý: giọng nói là dữ liệu cá nhân (Nghị định 13/2023); nội dung '
      + 'tạo bằng AI phải ghi nhãn (Nghị định 147/2024). Chỉ clone giọng của mình hoặc '
      + 'giọng đã được chủ giọng cho phép.</p></div>';

    var statusEl = el.querySelector('#settings-status');
    var voiceEl = el.querySelector('#settings-default-voice');
    var speedEl = el.querySelector('#settings-default-speed');
    var precisionEl = el.querySelector('#settings-precision');
    var threadsEl = el.querySelector('#settings-threads');
    var outputDirEl = el.querySelector('#settings-output-dir');
    var modelDirEl = el.querySelector('#settings-model-dir');
    var historyDirEl = el.querySelector('#settings-history-dir');
    var v4StatusEl = el.querySelector('#settings-v4-status');
    var v4KeyEl = el.querySelector('#settings-v4-key');
    var v4EstimateEl = el.querySelector('#settings-v4-estimate');
    var warnCharsEl = el.querySelector('#settings-warn-chars');
    var portEl = el.querySelector('#settings-server-port');
    var lanEl = el.querySelector('#settings-lan-enabled');
    var themeEl = el.querySelector('#settings-theme');
    var ffmpegStatusEl = el.querySelector('#settings-ffmpeg-status');
    var ffmpegBtn = el.querySelector('#settings-ffmpeg-download');
    var ffmpegProgressEl = el.querySelector('#settings-ffmpeg-progress');
    var ffmpegPercentEl = el.querySelector('#settings-ffmpeg-percent');
    var ffmpegTimer = null;
    var cfg = null;

    function setStatus(msg, isErr) {
      statusEl.textContent = msg || '';
      statusEl.className = isErr ? 'hp-error' : '';
    }

    function updateV4Estimate() {
      var warn = parseInt(warnCharsEl.value, 10);
      if (!warn || warn <= 0) { warn = 100000; }
      var est = api() ? api().estimateV4Cost('x'.repeat(Math.min(warn, 1000)))
        : { tokens: Math.max(50, Math.min(warn, 1000)) * 3.4 };
      v4EstimateEl.textContent = 'V4 tính phí theo ký tự: ký tự (tối thiểu 50/request) '
        + '× billingMultiplier × globalMultiplier. Ngưỡng cảnh báo hiện tại: '
        + warn.toLocaleString('vi-VN') + ' ký tự/phiên — vượt ngưỡng thì app cảnh báo '
        + 'trước khi gửi. Hệ số ví dụ trong OpenAPI là 3,4 (số thật lấy từ '
        + 'GET /v1/engines khi có key; phí thật ' + Math.round(est.tokens)
        + ' token cho 1.000 ký tự theo hệ số ví dụ).';
    }

    function refreshV4Status() {
      hpFetch('/api/config').then(function (c) {
        cfg = c;
        if (c.v4_configured) {
          v4StatusEl.textContent = 'Đã có key V4 (lưu qua keyring, không hiện lại key). '
            + 'Trạng thái "key hợp lệ / lỗi" chưa kiểm tra được — server chưa có '
            + 'endpoint kiểm tra số dư (GET /v1/balance); chỉ kiểm tra thật khi có '
            + 'endpoint hoặc khi tạo bằng V4 lần đầu (401 = key sai, 403 = hết quota).';
        } else {
          v4StatusEl.textContent = 'Chưa có key V4 — V4 đang tắt, app dùng V3 local '
            + '(miễn phí). Nhập key ở trên để bật V4.';
        }
      }).catch(function (err) {
        v4StatusEl.textContent = 'Không đọc được trạng thái key V4: ' + (err.message || err)
          + ' — kiểm tra server đã chạy ở 127.0.0.1:8124 chưa.';
      });
    }

    function refreshFfmpegStatus() {
      hpFetch('/api/ffmpeg/status').then(function (st) {
        var dl = st.download || {};
        if (st.available) {
          ffmpegStatusEl.textContent = 'Đã có FFmpeg (' + ffmpegKindLabel(st.kind) + '): '
            + (st.path || '') + (st.license ? ' — ' + st.license : '')
            + ' Xuất MP3 được.';
          ffmpegBtn.disabled = true;
          showFfmpegProgress(dl);
        } else {
          ffmpegStatusEl.textContent = (st.message || 'Chưa có FFmpeg — chỉ xuất được WAV.')
            + ' Bấm "Tải FFmpeg" để tải bản LGPL về lần đầu.';
          ffmpegBtn.disabled = dl.status === 'downloading';
          showFfmpegProgress(dl);
          if (dl.status === 'downloading') { pollFfmpeg(); }
        }
      }).catch(function (err) {
        ffmpegStatusEl.textContent = 'Không đọc được trạng thái FFmpeg: ' + (err.message || err)
          + ' — kiểm tra server đã chạy ở 127.0.0.1:8124 chưa.';
      });
    }

    function ffmpegKindLabel(kind) {
      return { system: 'FFmpeg hệ thống', downloaded: 'FFmpeg LGPL tải về',
               wheel: 'FFmpeg đi kèm wheel (máy dev)',
               other: 'FFmpeg', none: 'chưa có FFmpeg' }[kind] || kind;
    }

    function showFfmpegProgress(dl) {
      var downloading = dl && dl.status === 'downloading';
      ffmpegProgressEl.style.display = downloading ? '' : 'none';
      if (downloading) {
        ffmpegProgressEl.value = dl.percent || 0;
        ffmpegPercentEl.textContent = (dl.percent || 0) + '% — '
          + (dl.stage === 'verifying' ? 'đang kiểm tra checksum + giải nén…'
             : 'đang tải…');
      } else if (dl && dl.status === 'done') {
        ffmpegPercentEl.textContent = '100% — đã xong.';
      } else {
        ffmpegPercentEl.textContent = '';
      }
    }

    function stopFfmpegPoll() {
      if (ffmpegTimer) { clearInterval(ffmpegTimer); ffmpegTimer = null; }
    }

    function pollFfmpeg() {
      stopFfmpegPoll();
      ffmpegTimer = setInterval(function () {
        hpFetch('/api/ffmpeg/download').then(function (dl) {
          showFfmpegProgress(dl);
          if (dl.status === 'done') {
            stopFfmpegPoll();
            toast('Đã có FFmpeg — xuất MP3 được.', 'info');
            refreshFfmpegStatus();
          } else if (dl.status === 'error') {
            stopFfmpegPoll();
            ffmpegStatusEl.textContent = 'Tải FFmpeg lỗi: ' + (dl.message || '')
              + ' Kiểm tra mạng rồi bấm "Tải FFmpeg" lại, hoặc cài FFmpeg hệ thống.';
            ffmpegBtn.disabled = false;
            toast('Tải FFmpeg lỗi: ' + (dl.message || ''), 'error');
          }
        }).catch(function (err) {
          stopFfmpegPoll();
          ffmpegStatusEl.textContent = 'Không đọc được tiến trình tải FFmpeg: '
            + (err.message || err) + ' — kiểm tra server rồi bấm tải lại.';
        });
      }, 1000);
    }

    function loadAll() {
      hpFetch('/voices').then(function (voices) {
        voiceEl.innerHTML = (voices || []).map(function (v) {
          return '<option value="' + esc(v.id) + '">' + esc(v.name) + '</option>';
        }).join('') || '<option value="">— Không có giọng nào —</option>';
        return hpFetch('/api/config');
      }).then(function (c) {
        cfg = c;
        var audio = c.audio || {};
        var v3 = (c.engine && c.engine.v3) || {};
        var v4 = (c.engine && c.engine.v4) || {};
        var server = c.server || {};
        var storage = c.storage || {};
        if (audio.default_voice && voiceEl.querySelector('option[value="' + audio.default_voice + '"]')) {
          voiceEl.value = audio.default_voice;
        }
        speedEl.value = audio.default_speed != null ? audio.default_speed : 1;
        precisionEl.value = v3.precision || 'auto';
        threadsEl.value = v3.threads != null ? v3.threads : 0;
        outputDirEl.value = storage.output_dir || '';
        modelDirEl.value = v3.model_dir || '';
        historyDirEl.value = storage.history_dir || '';
        warnCharsEl.value = v4.warn_chars != null ? v4.warn_chars : 100000;
        portEl.value = server.port != null ? server.port : 8124;
        lanEl.checked = !!server.lan_enabled;
        themeEl.value = document.documentElement.getAttribute('data-theme') || 'light';
        updateV4Estimate();
        refreshV4Status();
      }).catch(function (err) {
        setStatus('Không tải được cài đặt: ' + (err.message || err)
          + ' — kiểm tra server đã chạy ở 127.0.0.1:8124 chưa, rồi tải lại tab.', true);
      });
    }

    el.querySelector('#settings-save-btn').addEventListener('click', function () {
      var speed = parseFloat(speedEl.value);
      if (speed < 0.75 || speed > 1.5) {
        toast('Tốc độ mặc định phải trong 0,75×–1,5×, nhận ' + speedEl.value + '×.', 'error');
        return;
      }
      var port = parseInt(portEl.value, 10);
      if (!port || port < 1 || port > 65535) {
        toast('Cổng API phải trong 1–65535, nhận ' + portEl.value + '.', 'error');
        return;
      }
      var patch = {
        audio: { default_voice: voiceEl.value, default_speed: speed },
        engine: {
          v3: { precision: precisionEl.value, threads: parseInt(threadsEl.value, 10) || 0,
                model_dir: modelDirEl.value.trim() },
          v4: { warn_chars: parseInt(warnCharsEl.value, 10) || 100000 }
        },
        server: { port: port, lan_enabled: lanEl.checked },
        storage: { output_dir: outputDirEl.value.trim(),
                   history_dir: historyDirEl.value.trim() }
      };
      hpFetch('/api/config', { method: 'POST', body: JSON.stringify(patch) })
        .then(function () {
          setStatus('Đã lưu cài đặt. Đổi cổng API hoặc precision cần khởi động lại server '
            + 'mới có hiệu lực.');
          toast('Đã lưu cài đặt.', 'info');
        })
        .catch(function (err) {
          setStatus('Không lưu được cài đặt: ' + (err.message || err)
            + ' — kiểm tra server rồi thử lại.', true);
          toast('Không lưu được cài đặt: ' + (err.message || err), 'error');
        });
    });

    el.querySelector('#settings-v4-save').addEventListener('click', function () {
      var key = v4KeyEl.value.trim();
      if (!key) {
        toast('Chưa nhập key — nhập key V4 (vn_sk_...) rồi bấm Lưu key, '
          + 'hoặc bấm Xoá key để gỡ key hiện tại.', 'error');
        return;
      }
      hpFetch('/api/config/v4-key', { method: 'POST', body: JSON.stringify({ api_key: key }) })
        .then(function (res) {
          v4KeyEl.value = '';
          toast(res.configured ? 'Đã lưu key V4 (qua keyring, không hiện lại).'
            : 'Key V4 chưa được lưu — thử lại.', res.configured ? 'info' : 'error');
          refreshV4Status();
        })
        .catch(function (err) {
          toast('Không lưu được key V4: ' + (err.message || err)
            + ' — kiểm tra server rồi thử lại. Key không được ghi log.', 'error');
        });
    });

    el.querySelector('#settings-v4-clear').addEventListener('click', function () {
      hpFetch('/api/config/v4-key', { method: 'POST', body: JSON.stringify({ api_key: '' }) })
        .then(function () {
          v4KeyEl.value = '';
          toast('Đã xoá key V4 — V4 tắt, app dùng V3 local.', 'info');
          refreshV4Status();
        })
        .catch(function (err) {
          toast('Không xoá được key V4: ' + (err.message || err) + ' — thử lại.', 'error');
        });
    });

    el.querySelector('#settings-ffmpeg-download').addEventListener('click', function () {
      ffmpegBtn.disabled = true;
      hpFetch('/api/ffmpeg/download', { method: 'POST' })
        .then(function (st) {
          var dl = (st && st.download) || {};
          if (st.available) {
            toast('Đã có FFmpeg — xuất MP3 được.', 'info');
            refreshFfmpegStatus();
          } else if (dl.status === 'downloading') {
            showFfmpegProgress(dl);
            pollFfmpeg();
          } else if (dl.status === 'error') {
            ffmpegBtn.disabled = false;
            ffmpegStatusEl.textContent = 'Tải FFmpeg lỗi: ' + (dl.message || '')
              + ' Kiểm tra mạng rồi bấm "Tải FFmpeg" lại, hoặc cài FFmpeg hệ thống.';
            toast('Tải FFmpeg lỗi: ' + (dl.message || ''), 'error');
          } else {
            refreshFfmpegStatus();
          }
        })
        .catch(function (err) {
          ffmpegBtn.disabled = false;
          toast('Không bắt đầu tải được FFmpeg: ' + (err.message || err)
            + ' — kiểm tra server rồi thử lại.', 'error');
        });
    });

    el.querySelector('#settings-generate-lan-key').addEventListener('click', function () {
      var key = randomKey();
      el.querySelector('#settings-lan-key-value').textContent = key;
      toast('Đã tạo khoá LAN mới — sao chép và lưu lại. Lưu ý: server v1 chưa có '
        + 'endpoint lưu key LAN nên khoá này chưa được server áp dụng.', 'info');
    });

    themeEl.addEventListener('change', function () {
      if (typeof NS.applyTheme === 'function') { NS.applyTheme(themeEl.value); }
      else { document.documentElement.setAttribute('data-theme', themeEl.value); }
    });
    warnCharsEl.addEventListener('input', updateV4Estimate);

    loadAll();
    refreshFfmpegStatus();
  }

  registerTab({ id: 'settings', group: 'Hệ thống', label: 'Cài đặt', render: render });
})();
