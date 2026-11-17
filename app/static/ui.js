/* Presentation only: native forms/links still go through Flask authorization. */
(() => {
  'use strict';
  const body = document.body;
  const sidebar = document.getElementById('sidebar');
  const toggle = document.querySelector('.sidebar-toggle');
  const mobile = window.matchMedia('(max-width: 900px)');
  function syncSidebar() {
    if (!sidebar || !toggle) return;
    const expanded = mobile.matches ? body.classList.contains('sidebar-open') : !body.classList.contains('sidebar-collapsed');
    toggle.setAttribute('aria-expanded', String(expanded));
    sidebar.inert = mobile.matches && !expanded;
  }
  function closeSidebar() {
    body.classList.remove('sidebar-open');
    syncSidebar();
  }
  if (sidebar && toggle) {
    try { body.classList.toggle('sidebar-collapsed', localStorage.getItem('fg-sidebar') === 'compact'); } catch (_) { /* storage is optional */ }
    toggle.addEventListener('click', () => {
      if (mobile.matches) {
        body.classList.toggle('sidebar-open');
        syncSidebar();
        if (body.classList.contains('sidebar-open')) sidebar.querySelector('a')?.focus();
      } else {
        body.classList.toggle('sidebar-collapsed');
        try { localStorage.setItem('fg-sidebar', body.classList.contains('sidebar-collapsed') ? 'compact' : 'full'); } catch (_) { /* optional */ }
        syncSidebar();
      }
    });
    document.querySelector('.sidebar-backdrop')?.addEventListener('click', () => { closeSidebar(); toggle.focus(); });
    sidebar.querySelectorAll('a').forEach(link => link.addEventListener('click', () => { if (mobile.matches) closeSidebar(); }));
    document.addEventListener('keydown', event => {
      if (!mobile.matches || !body.classList.contains('sidebar-open')) return;
      if (event.key === 'Escape') { closeSidebar(); toggle.focus(); }
      if (event.key === 'Tab') {
        const links = [...sidebar.querySelectorAll('a[href],button')];
        const first = links[0], last = links[links.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    });
    mobile.addEventListener('change', closeSidebar);
    syncSidebar();
    const updateActive = () => {
      if (!location.pathname.endsWith('/dashboard')) return;
      const fragment = location.hash === '#security-logs' ? '#security-logs' : '#overview';
      sidebar.querySelectorAll('a.side-link').forEach(link => {
        const active = link.getAttribute('href').endsWith(fragment);
        link.classList.toggle('active', active);
        if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
      });
    };
    window.addEventListener('hashchange', updateActive);
    updateActive();
  }

  const search = document.getElementById('file-search');
  const type = document.getElementById('file-type');
  const rows = [...document.querySelectorAll('[data-file-path]')];
  const normalized = text => text.normalize('NFC').toLocaleLowerCase('vi');
  const extension = path => {
    const filename = path.split('/').pop();
    return filename.includes('.') ? filename.split('.').pop().toLowerCase() : '(không đuôi)';
  };
  if (search && type) {
    [...new Set(rows.map(row => extension(row.dataset.filePath)))].sort().forEach(ext => {
      const option = document.createElement('option'); option.value = ext; option.textContent = ext.toUpperCase(); type.append(option);
    });
    const filter = () => {
      let visible = 0;
      rows.forEach(row => {
        row.hidden = !normalized(row.dataset.filePath).includes(normalized(search.value)) || (type.value !== '' && extension(row.dataset.filePath) !== type.value);
        if (!row.hidden) visible += 1;
      });
      document.getElementById('file-no-match').hidden = rows.length === 0 || visible > 0;
      document.getElementById('file-result-count').textContent = `${visible} / ${rows.length} tệp trong danh sách đang hiển thị. Tìm kiếm không gửi yêu cầu tải.`;
    };
    search.addEventListener('input', filter); type.addEventListener('change', filter);
    document.querySelector('[data-file-tools]').hidden = false;
    filter();
  }

  // A native attachment response has no reliable completion callback. Never
  // report success without a backend response; errors use Flask's error page.
  function pendingDownload(button) {
    const status = document.getElementById('download-feedback');
    if (status) status.textContent = 'Đã gửi yêu cầu tải. Backend sẽ xác minh; xem thông báo lỗi hoặc tệp tải trong trình duyệt.';
    if (button) { button.setAttribute('aria-busy', 'true'); window.setTimeout(() => button.removeAttribute('aria-busy'), 1800); }
  }
  document.querySelector('[data-download-form]')?.addEventListener('submit', event => pendingDownload(event.target.querySelector('button')));
  document.querySelectorAll('[data-download-link]').forEach(link => link.addEventListener('click', event => { if (!event.ctrlKey && !event.metaKey) pendingDownload(link); }));
  const password = document.getElementById('pw');
  const reveal = document.getElementById('password-toggle');
  if (password && reveal) {
    reveal.hidden = false;
    reveal.addEventListener('click', () => {
      const visible = password.type === 'password';
      password.type = visible ? 'text' : 'password';
      reveal.textContent = visible ? 'Ẩn' : 'Hiện';
      reveal.setAttribute('aria-pressed', String(visible));
      reveal.setAttribute('aria-label', visible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu');
    });
  }
  const originalLabels = new WeakMap();
  document.querySelectorAll('[data-navigation-form]').forEach(form => form.addEventListener('submit', () => {
    // Do not target the password toggle or change submitted fields/CSRF.
    const button = form.querySelector('button[type="submit"],button:not([type])');
    if (!button) return;
    button.setAttribute('aria-busy', 'true');
    if (button.dataset.loadingLabel) {
      if (!originalLabels.has(button)) originalLabels.set(button, button.textContent);
      button.textContent = button.dataset.loadingLabel;
    }
  }));
  window.addEventListener('pageshow', () => {
    document.querySelectorAll('[aria-busy=true]').forEach(node => {
      node.removeAttribute('aria-busy');
      if (originalLabels.has(node)) node.textContent = originalLabels.get(node);
    });
    if (password && reveal) {
      password.type = 'password';
      reveal.textContent = 'Hiện';
      reveal.setAttribute('aria-pressed', 'false');
      reveal.setAttribute('aria-label', 'Hiện mật khẩu');
    }
  });
})();
