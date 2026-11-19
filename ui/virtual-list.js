/* HP Voice Studio — Danh sách ảo (VirtualList) (TK3.7, TH-28).
 *
 * Chỉ render các hàng đang thấy trong viewport (+ vài hàng đệm), không render
 * toàn bộ 100–500 mục của batch/lịch sử. Mỗi hàng có chiều cao CỐ ĐỊNH
 * (itemHeight, px) để tính được vị trí bằng phép nhân — không đo DOM từng hàng.
 *
 * Cách dùng:
 *   var list = new window.HPVoiceStudio.VirtualList(containerEl, {
 *     itemHeight: 44,
 *     items: [...],
 *     renderItem: function (item, index) { return '<div>...</div>'; },
 *     overscan: 5
 *   });
 *   list.setItems(moiDanhSach);   // đổi dữ liệu, render lại vùng đang thấy
 *   list.refresh();               // render lại (sau khi cuộn/kéo giãn)
 *   list.destroy();               // gỡ listener khi tab bị hủy
 */
(function () {
  'use strict';

  var NS = window.HPVoiceStudio = window.HPVoiceStudio || {};

  function VirtualList(container, options) {
    if (!container) { throw new Error('VirtualList cần 1 phần tử container.'); }
    options = options || {};
    this.container = container;
    this.itemHeight = options.itemHeight || 48;
    this.items = options.items || [];
    this.renderItem = options.renderItem || function (item) { return String(item); };
    this.overscan = (options.overscan == null) ? 5 : options.overscan;
    this.onRowClick = options.onRowClick || null;

    // Khung cuộn: chiều cao cố định, chỉ vùng này cuộn (viewport của list).
    this.container.style.overflowY = 'auto';
    this.container.style.position = 'relative';
    this.container.classList.add('hp-virtual-list');

    // Spacer giữ tổng chiều cao thật của danh sách để thanh cuộn đúng tỉ lệ;
    // các hàng đang thấy được đặt tuyệt đối bên trong spacer.
    this.spacer = document.createElement('div');
    this.spacer.style.position = 'relative';
    this.spacer.style.width = '100%';
    this.container.appendChild(this.spacer);

    var self = this;
    this._onScroll = function () { self.render(); };
    this.container.addEventListener('scroll', this._onScroll, { passive: true });
    this.render();
  }

  /** Tính khoảng hàng đang thấy từ vị trí cuộn của viewport. */
  VirtualList.prototype.visibleRange = function () {
    var scrollTop = this.container.scrollTop || 0;
    var viewportHeight = this.container.clientHeight || 0;
    var total = this.items.length;
    var start = Math.max(0, Math.floor(scrollTop / this.itemHeight) - this.overscan);
    var end = Math.min(
      total,
      Math.ceil((scrollTop + viewportHeight) / this.itemHeight) + this.overscan
    );
    return { start: start, end: end, total: total, scrollTop: scrollTop, viewportHeight: viewportHeight };
  };

  /** Chỉ render các hàng trong khoảng đang thấy (kèm đệm overscan). */
  VirtualList.prototype.render = function () {
    var range = this.visibleRange();
    this.spacer.style.height = (range.total * this.itemHeight) + 'px';
    var html = '';
    for (var i = range.start; i < range.end; i++) {
      html += '<div class="hp-vrow" data-index="' + i + '" style="position:absolute;'
        + 'left:0;right:0;top:' + (i * this.itemHeight) + 'px;height:' + this.itemHeight + 'px;'
        + 'overflow:hidden;">' + this.renderItem(this.items[i], i) + '</div>';
    }
    this.spacer.innerHTML = html;
    // Số hàng DOM thực tế luôn nhỏ (khoảng đang thấy + đệm), không tăng theo tổng số mục.
    this.renderedCount = range.end - range.start;
    this.visibleStart = range.start;
    this.visibleEnd = range.end;
  };

  VirtualList.prototype.setItems = function (items) {
    this.items = items || [];
    this.render();
  };

  VirtualList.prototype.refresh = function () { this.render(); };

  VirtualList.prototype.destroy = function () {
    this.container.removeEventListener('scroll', this._onScroll);
    this.container.innerHTML = '';
  };

  NS.VirtualList = VirtualList;
})();
