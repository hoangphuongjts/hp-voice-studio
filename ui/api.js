/* HP Voice Studio — api.js (TK3.1/TK3.6).
 *
 * Fetch wrapper cho API local (loopback http://127.0.0.1:8124):
 * - Mọi lỗi trả về đều dùng envelope chuẩn {"error": {code, message}} (SPEC §4)
 *   và được chuyển thành thông báo tiếng Việt rõ lý do + cách sửa — không bao
 *   giờ hiện "lỗi chung chung".
 * - Ước tính phí V4: ký tự (tối thiểu 50/request) × billingMultiplier ×
 *   globalMultiplier (TH-05). Hệ số mặc định 3.4 chỉ là VÍ DỤ trong OpenAPI
 *   GET /v1/engines — số thật chỉ biết khi gọi API với key thật (chờ kiểm
 *   chứng thật, xem docs/v4-billing.md).
 */
(function () {
  'use strict';

  var NS = window.HPVoiceStudio = window.HPVoiceStudio || {};

  var API_BASE = 'http://127.0.0.1:8124';
  var MIN_BILLABLE_CHARS = 50;
  var V4_EXAMPLE_MULTIPLIER = 3.4; // ví dụ trong OpenAPI, không phải số thật
  var V4_GLOBAL_MULTIPLIER = 1.0;

  /** Chuyển lỗi API/thất bại mạng thành câu tiếng Việt rõ lý do + cách sửa. */
  function formatError(err, fallback) {
    if (!err) { return fallback || 'Đã xảy ra lỗi không rõ nguyên nhân.'; }
    var msg = (err && err.message) ? err.message : String(err);
    if (msg === 'Failed to fetch' || msg.indexOf('NetworkError') !== -1
        || msg.indexOf('network') !== -1) {
      return 'Không kết nối được máy chủ local ' + API_BASE
        + ' — kiểm tra server HP Voice Studio đã chạy chưa (cổng 8124), '
        + 'rồi thử lại.';
    }
    return msg;
  }

  /** Đọc body lỗi chuẩn {"error": {code, message}}; không parse được thì trả text. */
  function readError(resp, bodyText) {
    try {
      var data = JSON.parse(bodyText);
      if (data && data.error && data.error.message) {
        return new Error(data.error.message
          + ' (mã ' + (data.error.code || resp.status) + ')');
      }
      if (data && data.detail) { return new Error(String(data.detail)); }
    } catch (e) { /* body không phải JSON */ }
    if (bodyText) { return new Error(bodyText); }
    return new Error('Máy chủ trả lỗi HTTP ' + resp.status
      + ' mà không kèm lý do — thử lại, nếu vẫn lỗi thì khởi động lại server.');
  }

  /** Request thô: trả Response (để tab tự xử lý audio bytes / ZIP / 202 job). */
  function requestRaw(path, options) {
    options = options || {};
    var headers = {};
    if (options.body && typeof options.body === 'string') {
      headers['Content-Type'] = 'application/json';
    }
    if (options.headers) {
      for (var k in options.headers) { headers[k] = options.headers[k]; }
    }
    return fetch(API_BASE + path, {
      method: options.method || 'GET',
      headers: headers,
      body: options.body
    }).catch(function (err) {
      throw new Error(formatError(err));
    });
  }

  /** Request JSON: 2xx -> object; lỗi -> Error mang message rõ lý do + cách sửa. */
  function request(path, options) {
    return requestRaw(path, options).then(function (resp) {
      return resp.text().then(function (text) {
        if (resp.ok) {
          if (!text) { return {}; }
          try { return JSON.parse(text); }
          catch (e) { return { raw: text }; }
        }
        throw readError(resp, text);
      });
    });
  }

  /** GET JSON. Dùng cho /health, /voices, /api/config, /api/dict, /api/jobs/... */
  function fetchJson(path, options) {
    return request(path, options || {});
  }

  function getJson(path) { return request(path, {}); }

  function postJson(path, body) {
    return request(path, { method: 'POST', body: JSON.stringify(body || {}) });
  }

  /** Ước tính phí V4 (token) cho 1 request: max(50, ký tự) × multiplier × global. */
  function estimateV4Cost(text, engineMultiplier, globalMultiplier) {
    var chars = String(text == null ? '' : text).length;
    var billable = Math.max(MIN_BILLABLE_CHARS, chars);
    var mult = (engineMultiplier == null) ? V4_EXAMPLE_MULTIPLIER : engineMultiplier;
    var glob = (globalMultiplier == null) ? V4_GLOBAL_MULTIPLIER : globalMultiplier;
    return { chars: chars, billable: billable, tokens: billable * mult * glob,
             multiplier: mult, globalMultiplier: glob };
  }

  /** Câu cảnh báo phí V4 hiển thị TRƯỚC khi gửi (TK3.6). */
  function v4FeeNote(text, engineMultiplier) {
    var est = estimateV4Cost(text, engineMultiplier);
    return 'V4 tính phí theo ký tự: ' + est.chars + ' ký tự (tính tối thiểu '
      + MIN_BILLABLE_CHARS + '/request) × ' + est.multiplier + ' ≈ '
      + Math.round(est.tokens) + ' token. Hệ số ' + est.multiplier
      + ' là ví dụ trong OpenAPI — số thật lấy từ GET /v1/engines khi có key.';
  }

  NS.api = {
    base: API_BASE,
    MIN_BILLABLE_CHARS: MIN_BILLABLE_CHARS,
    V4_EXAMPLE_MULTIPLIER: V4_EXAMPLE_MULTIPLIER,
    request: request,
    requestRaw: requestRaw,
    fetchJson: fetchJson,
    getJson: getJson,
    postJson: postJson,
    formatError: formatError,
    estimateV4Cost: estimateV4Cost,
    v4FeeNote: v4FeeNote
  };
})();
