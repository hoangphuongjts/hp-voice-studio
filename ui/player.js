/* HP Voice Studio — Trình phát dùng chung (TK3.7, TH-28).
 *
 * SINGLETON: toàn app chỉ có DUY NHẤT 1 thẻ Audio (dòng `new Audio()` dưới
 * đây là lần duy nhất trong toàn bộ UI). Mọi tab nghe lại đều phải qua
 * `window.HPVoiceStudio.player`, KHÔNG được tự tạo `new Audio()` riêng —
 * nếu không, batch 100–500 mục sẽ phình RAM trình duyệt và nhiều bản phát
 * chồng lên nhau. Phát mới tự dừng phát cũ.
 */
(function () {
  'use strict';

  var NS = window.HPVoiceStudio = window.HPVoiceStudio || {};

  // Thẻ Audio duy nhất của toàn app.
  var audio = new Audio();
  audio.preload = 'auto';

  var currentUrl = null;      // URL đang phát (blob: hoặc http://...)
  var currentBlobUrl = null;  // blob URL do player tự tạo thì tự thu hồi
  var currentLabel = '';
  var listeners = [];         // callback onStateChange(state)

  function state() {
    return {
      url: currentUrl,
      label: currentLabel,
      paused: audio.paused,
      playing: !audio.paused && !audio.ended && !!currentUrl,
      currentTime: audio.currentTime || 0,
      duration: isFinite(audio.duration) ? audio.duration : 0
    };
  }

  function notify() {
    var s = state();
    listeners.forEach(function (fn) {
      try { fn(s); } catch (e) { /* callback tab lỗi không được làm chết player */ }
    });
  }

  audio.addEventListener('ended', function () { notify(); });
  audio.addEventListener('pause', function () { notify(); });
  audio.addEventListener('play', function () { notify(); });
  audio.addEventListener('error', function () { notify(); });

  /** Phát 1 URL. Phát mới luôn dừng phát cũ trước (TH-28). */
  function play(url, label) {
    if (!url) { return Promise.reject(new Error('Không có URL audio để phát.')); }
    // Dừng phát cũ: đổi nguồn là đủ, nhưng pause() tường minh để chắc chắn
    // không còn tiếng cũ khi đổi src trên trình duyệt cũ.
    try { audio.pause(); } catch (e) { /* bỏ qua */ }
    if (currentBlobUrl && currentBlobUrl !== url) {
      try { URL.revokeObjectURL(currentBlobUrl); } catch (e) { /* bỏ qua */ }
      currentBlobUrl = null;
    }
    currentUrl = url;
    currentLabel = label || url;
    audio.src = url;
    audio.currentTime = 0;
    var p = audio.play();
    if (p && typeof p.catch === 'function') {
      p.catch(function (err) {
        // Trình duyệt chặn autoplay khi chưa có tương tác: báo rõ, không im lặng.
        notify();
        throw err;
      });
    }
    notify();
    return Promise.resolve();
  }

  /** Phát 1 Blob audio (WAV/MP3): tự tạo blob URL, tự thu hồi khi phát mới. */
  function playBlob(blob, label) {
    var url = URL.createObjectURL(blob);
    currentBlobUrl = url;
    return play(url, label);
  }

  function pause() {
    try { audio.pause(); } catch (e) { /* bỏ qua */ }
    notify();
  }

  function stop() {
    try { audio.pause(); } catch (e) { /* bỏ qua */ }
    audio.removeAttribute('src');
    try { audio.load(); } catch (e) { /* bỏ qua */ }
    if (currentBlobUrl) {
      try { URL.revokeObjectURL(currentBlobUrl); } catch (e) { /* bỏ qua */ }
      currentBlobUrl = null;
    }
    currentUrl = null;
    currentLabel = '';
    notify();
  }

  function toggle(url, label) {
    if (currentUrl === url && !audio.paused) { pause(); return Promise.resolve(); }
    return play(url, label);
  }

  NS.player = {
    play: play,
    playBlob: playBlob,
    pause: pause,
    stop: stop,
    toggle: toggle,
    getState: state,
    onStateChange: function (fn) { if (typeof fn === 'function') { listeners.push(fn); } },
    // Chỉ đọc, phục vụ test/kiểm chứng: đúng 1 thẻ Audio dùng chung.
    _audioElement: audio
  };
})();
