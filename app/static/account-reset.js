/* A URL fragment is never sent in HTTP requests or server access logs. */
(() => {
  'use strict';
  const token = new URLSearchParams(location.hash.slice(1)).get('token');
  if (location.hash) history.replaceState(null, '', location.pathname);
  if (token && /^[A-Za-z0-9_-]{43}$/.test(token)) document.getElementById('reset-token').value = token;
})();
