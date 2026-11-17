/* Presentation preference only; apply before styles and first paint. */
(() => {
  'use strict';
  const root = document.documentElement;
  const sizes = {small:16, medium:18, large:20};
  const key = 'fg-text-size';
  let selected = 'medium';
  const valid = value => Object.hasOwn(sizes, value) ? value : 'medium';
  try { selected = valid(localStorage.getItem(key)); } catch (_) { /* memory fallback */ }
  function apply() {
    root.dataset.textSize = selected;
    root.style.setProperty('--base-font-size', sizes[selected]+'px');
    document.querySelectorAll('[data-text-size]').forEach(button => {
      if (button.tagName === 'BUTTON') button.setAttribute('aria-pressed',String(button.dataset.textSize === selected));
    });
    document.dispatchEvent(new CustomEvent('fileguard:textsizechange'));
  }
  function choose(value) {
    selected = valid(value);
    try { localStorage.setItem(key, selected); } catch (_) { /* memory fallback */ }
    apply();
  }
  apply();
  window.addEventListener('storage', event => {
    if (event.key === key || event.key === null) { selected = valid(event.newValue); apply(); }
  });
  document.addEventListener('DOMContentLoaded', () => {
    const controls = document.getElementById('text-size-controls');
    if (!controls) return;
    controls.hidden = false;
    controls.querySelectorAll('button').forEach(button => button.addEventListener('click', () => choose(button.dataset.textSize)));
    apply();
  }, {once:true});
})();
