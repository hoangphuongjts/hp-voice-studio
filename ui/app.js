/* HP Voice Studio — app.js (TK3.1/TK3.6). Shell chính, nạp CUỐI CÙNG.
 *
 * - Registry tab: window.HPVoiceStudio.registerTab({id, group, label, render}).
 *   Các file tabs-*.js nạp TRƯỚC app.js nên khi đó registerTab chưa có — chúng
 *   đẩy tab vào window.HPVoiceStudio._pendingTabs; app.js khởi động sẽ nhận
 *   hết tab chờ rồi mới render nav. Tab nào chưa nạp (file thiếu) thì nav chỉ
 *   hiện tab đã đăng ký, không crash.
 * - Nhóm nav theo SPEC §5: Tạo / Thư viện / Hệ thống.
 * - Header luôn thấy trạng thái engine (poll GET /health, TK3.6).
 * - Toast lỗi luôn nêu rõ lý do + cách sửa (TK3.6).
 * - KHÔNG tạo Audio mới — nghe lại dùng window.HPVoiceStudio.player (TK3.7).
 */
(function () {
  'use strict';

  var NS = window.HPVoiceStudio = window.HPVoiceStudio || {};
  var GROUP_ORDER = ['Tạo', 'Thư viện', 'Hệ thống'];
  var registry = [];
  var currentTabId = null;
  var healthTimer = null;

  function api() { return NS.api || null; }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>\"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /** Đăng ký 1 tab. Tab trùng id thì bản đăng ký sau thắng (ghi đè). */
  function registerTab(def) {
    if (!def || !def.id || !def.label || typeof def.render !== 'function') {
      // eslint-disable-next-line no-console
      console.warn('Bỏ qua tab đăng ký thiếu id/label/render:', def);
      return;
    }
    def.group = GROUP_ORDER.indexOf(def.group) !== -1 ? def.group : 'Tạo';
    var found = false;
    for (var i = 0; i < registry.length; i++) {
      if (registry[i].id === def.id) { registry[i] = def; found = true; break; }
    }
    if (!found) { registry.push(def); }
    if (currentTabId === null) { renderNav(); }
    else if (document.getElementById('app-nav')) { renderNav(); }
  }

  /** Nhận hết tab các file nạp trước đã đẩy vào _pendingTabs. */
  function drainPendingTabs() {
    var pending = NS._pendingTabs || [];
    NS._pendingTabs = [];
    pending.forEach(function (def) { registerTab(def); });
  }

  function tabs() { return registry.slice(); }

  /** Render nav trái từ registry (chỉ tab đã đăng ký mới hiện). */
  function renderNav() {
    var nav = document.getElementById('app-nav');
    if (!nav) { return; }
    var html = '';
    GROUP_ORDER.forEach(function (group) {
      var items = registry.filter(function (t) { return t.group === group; });
      if (!items.length) { return; }
      html += '<div class="hp-nav-group"><div class="hp-nav-group-title">'
        + esc(group) + '</div>';
      items.forEach(function (t) {
        html += '<button type="button" class="hp-nav-item'
          + (t.id === currentTabId ? ' hp-nav-item-active' : '')
          + '" data-tab="' + esc(t.id) + '">' + esc(t.label) + '</button>';
      });
      html += '</div>';
    });
    if (!registry.length) {
      html += '<p class="hp-hint">Chưa có tab nào được nạp.</p>';
    }
    nav.innerHTML = html;
    var buttons = nav.querySelectorAll('[data-tab]');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener('click', function (ev) {
        switchTab(ev.currentTarget.getAttribute('data-tab'));
      });
    }
  }

  /** Chuyển tab: gọi render(tab) của tab đó vào #tab-content. */
  function switchTab(id) {
    var tab = null;
    for (var i = 0; i < registry.length; i++) {
      if (registry[i].id === id) { tab = registry[i]; break; }
    }
    if (!tab) {
      toast('Không mở được tab "' + id + '" vì tab này chưa được nạp '
        + '(file tabs-' + id + '.js thiếu hoặc lỗi) — thử tải lại trang, '
        + 'nếu vẫn lỗi thì kiểm tra file ui/tabs-' + id + '.js có tồn tại không.', 'error');
      return false;
    }
    currentTabId = id;
    var content = document.getElementById('tab-content');
    if (content) {
      content.innerHTML = '';
      try { tab.render(content); }
      catch (err) {
        content.innerHTML = '<p class="hp-error">Không hiển thị được tab '
          + esc(tab.label) + ': ' + esc(err.message || err)
          + '. Thử tải lại trang.</p>';
      }
    }
    document.title = 'HP Voice Studio — ' + tab.label;
    renderNav();
    return true;
  }

  /** Toast: lỗi luôn nêu rõ lý do + cách sửa (TK3.6), không "lỗi chung chung". */
  function toast(message, kind) {
    kind = kind || 'info';
    var box = document.getElementById('toast-container');
    if (!box) {
      // Chưa có DOM (gọi quá sớm): log để không mất thông báo.
      // eslint-disable-next-line no-console
      console[kind === 'error' ? 'error' : 'log']('[HP Voice Studio] ' + message);
      return;
    }
    var el = document.createElement('div');
    el.className = 'hp-toast hp-toast-' + kind;
    el.setAttribute('role', kind === 'error' ? 'alert' : 'status');
    el.textContent = message;
    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'hp-toast-close';
    close.textContent = '×';
    close.setAttribute('aria-label', 'Đóng thông báo');
    close.addEventListener('click', function () { el.remove(); });
    el.appendChild(close);
    box.appendChild(el);
    setTimeout(function () { if (el.parentNode) { el.remove(); } },
      kind === 'error' ? 12000 : 6000);
  }

  function notify(message, kind) { toast(message, kind); }

  /** Trạng thái engine ở header: poll GET /health (TK3.6). */
  function updateEngineStatus() {
    var el = document.getElementById('engine-status');
    if (!el) { return; }
    var apiObj = api();
    if (!apiObj) {
      el.textContent = 'Trạng thái engine: chưa rõ (api.js chưa nạp).';
      return;
    }
    apiObj.fetchJson('/health').then(function (h) {
      var v3 = h.v3_ready ? 'V3 local: sẵn sàng' : 'V3 local: đang khởi động';
      var v4 = h.v4_configured ? 'V4: đã có key' : 'V4: chưa có key';
      el.textContent = v3 + ' · ' + v4;
      el.dataset.ready = h.v3_ready ? 'true' : 'false';
      var select = document.getElementById('engine-select');
      if (select && !select.dataset.userChanged) {
        select.value = h.engine || 'v3';
      }
    }).catch(function (err) {
      el.textContent = 'Không kết nối được API local — kiểm tra server đã chạy '
        + 'ở 127.0.0.1:8124 chưa (' + (err.message || err) + ').';
      el.dataset.ready = 'false';
    });
  }

  /** Giao diện sáng/tối: lưu trên trình duyệt này (localStorage). */
  function applyTheme(theme) {
    theme = (theme === 'dark') ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem('hp-voice-studio-theme', theme); } catch (e) { /* bỏ qua */ }
    var select = document.getElementById('settings-theme');
    if (select) { select.value = theme; }
  }

  function loadTheme() {
    var theme = 'light';
    try { theme = localStorage.getItem('hp-voice-studio-theme') || 'light'; } catch (e) { /* bỏ qua */ }
    applyTheme(theme);
  }

  function init() {
    drainPendingTabs();
    loadTheme();
    renderNav();
    // Tab mặc định: Phòng thu; nếu chưa nạp thì tab đầu tiên đã đăng ký.
    var first = null;
    for (var i = 0; i < registry.length; i++) {
      if (registry[i].id === 'studio') { first = 'studio'; break; }
    }
    if (!first && registry.length) { first = registry[0].id; }
    if (first) { switchTab(first); }
    var select = document.getElementById('engine-select');
    if (select) {
      select.addEventListener('change', function () {
        select.dataset.userChanged = 'true';
        toast('Đã chọn engine ' + select.value.toUpperCase()
          + ' cho lần tạo tiếp theo. V4 tính phí theo ký tự — xem ước tính phí '
          + 'trước khi bấm Tạo.', 'info');
      });
    }
    updateEngineStatus();
    healthTimer = setInterval(updateEngineStatus, 10000);
  }

  NS.registerTab = registerTab;
  NS.switchTab = switchTab;
  NS.tabs = tabs;
  NS.toast = toast;
  NS.notify = notify;
  NS.applyTheme = applyTheme;
  NS.updateEngineStatus = updateEngineStatus;
  NS._healthTimer = function () { return healthTimer; };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
