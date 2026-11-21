/* Local polling only; no browser/provider API key and no authorization decisions. */
(() => {
  'use strict';
  const root = document.getElementById('alert-live');
  if (!root) return;
  const status = document.getElementById('alert-live-status');
  const container = document.getElementById('alert-live-items');
  let cursor = null, failures = 0, shown = [];
  async function poll() {
    if (document.hidden) { setTimeout(poll, 5000); return; }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 4000);
    try {
      const url = root.dataset.feed + (cursor === null ? '' : '?after=' + cursor);
      const response = await fetch(url, {credentials:'same-origin', redirect:'error', signal:controller.signal, headers:{Accept:'application/json'}});
      if (!response.ok) throw new Error('unavailable');
      const data = await response.json();
      if (!Number.isSafeInteger(data.cursor) || !Array.isArray(data.items)) throw new Error('invalid');
      status.textContent = data.new_count + ' nhóm cảnh báo mới · ' + (data.enabled ? 'Đang theo dõi' : 'Thông báo đã tắt');
      const now = Date.now(); shown = shown.filter(time => now - time < 60000);
      for (const item of data.items) {
        if (shown.length >= 3) break;
        if (!Number.isSafeInteger(item.id) || !Number.isSafeInteger(item.last_event_id)) continue;
        const link = document.createElement('a');
        link.href = '/dashboard/events/' + item.last_event_id;
        link.textContent = 'Cảnh báo #' + item.id + ' · Ưu tiên ' + (item.priority === 'high' ? 'cao' : 'trung bình') + ' · Xem sự kiện';
        const paragraph = document.createElement('p'); paragraph.append(link); container.prepend(paragraph);
        while (container.children.length > 3) container.lastChild.remove();
        shown.push(now);
      }
      cursor = data.cursor; failures = 0;
    } catch (_) {
      failures += 1;
      status.textContent = 'Chưa cập nhật được cảnh báo. Có thể mở trang quản lý; hệ thống sẽ thử lại.';
    } finally {
      clearTimeout(timer);
      setTimeout(poll, Math.min(60000, 5000 * 2 ** Math.min(failures, 4)));
    }
  }
  poll();
})();
