/* Runs before styles: choose the resolved theme before the first page paint.
   Stores presentation preference only; never reads authentication/session data. */
(() => {
  'use strict';
  const key = 'fg-theme';
  const modes = ['light', 'dark', 'system'];
  const root = document.documentElement;
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  let preference = 'system';
  const valid = value => modes.includes(value) ? value : 'system';
  try { preference = valid(localStorage.getItem(key)); } catch (_) { /* memory fallback */ }
  const resolve = () => preference === 'system' ? (system.matches ? 'dark' : 'light') : preference;
  function apply() {
    const theme = resolve();
    root.dataset.bsTheme = theme;
    root.dataset.themePreference = preference;
    root.style.colorScheme = theme;
    document.dispatchEvent(new CustomEvent('fileguard:themechange', {detail:{theme, preference}}));
  }
  function choose(mode) {
    preference = valid(mode);
    try { localStorage.setItem(key, preference); } catch (_) { /* keep page usable */ }
    apply();
  }
  window.FileGuardTheme = Object.freeze({choose, preference:() => preference, resolved:resolve});
  system.addEventListener('change', () => { if (preference === 'system') apply(); });
  window.addEventListener('storage', event => { if (event.key === key || event.key === null) { preference = valid(event.newValue); apply(); } });
  apply();

  function controls() {
    const picker = document.getElementById('theme-picker');
    const toggle = document.getElementById('theme-toggle');
    const menu = document.getElementById('theme-menu');
    if (!picker || !toggle || !menu) return;
    const choices = [...menu.querySelectorAll('[data-theme-choice]')];
    const names = {light:'Sáng', dark:'Tối', system:'Theo hệ thống'};
    const close = focus => { menu.hidden = true; toggle.setAttribute('aria-expanded','false'); if (focus) toggle.focus(); };
    function sync() {
      picker.hidden = false;
      toggle.querySelector('[data-theme-icon]').textContent = resolve() === 'dark' ? '☾' : '☀';
      toggle.setAttribute('aria-label', `Giao diện: ${names[preference]} (${names[resolve()]}). Chọn Sáng, Tối hoặc Theo hệ thống`);
      toggle.title = `Giao diện: ${names[preference]}`;
      choices.forEach(button => button.setAttribute('aria-checked',String(button.dataset.themeChoice === preference)));
    }
    function open(last=false) {
      menu.hidden = false;
      // Account controls can wrap the trigger into the middle of a row.
      // Anchor the popup within the viewport instead of clipping to its parent.
      const bounds = toggle.getBoundingClientRect();
      menu.style.position = 'fixed';
      menu.style.right = 'auto';
      menu.style.left = Math.max(8, Math.min(bounds.right-menu.offsetWidth, innerWidth-menu.offsetWidth-8))+'px';
      menu.style.top = Math.max(8, Math.min(bounds.bottom+8, innerHeight-menu.offsetHeight-8))+'px';
      toggle.setAttribute('aria-expanded','true');
      const selected = choices.find(button => button.dataset.themeChoice === preference);
      (last ? choices[choices.length-1] : selected || choices[0]).focus();
    }
    toggle.addEventListener('click', () => menu.hidden ? open() : close(false));
    toggle.addEventListener('keydown', event => {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); open(event.key === 'ArrowUp'); }
    });
    choices.forEach(button => button.addEventListener('click', () => { choose(button.dataset.themeChoice); close(true); }));
    menu.addEventListener('keydown', event => {
      const index = choices.indexOf(document.activeElement);
      if (['ArrowDown','ArrowUp','Home','End'].includes(event.key)) {
        event.preventDefault();
        const next = event.key === 'Home' ? 0 : event.key === 'End' ? choices.length-1 : (index + (event.key === 'ArrowDown' ? 1 : -1) + choices.length) % choices.length;
        choices[next].focus();
      }
      if (event.key === 'Tab') close(false);
    });
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && !menu.hidden) { event.preventDefault(); close(true); } });
    document.addEventListener('click', event => { if (!picker.contains(event.target)) close(false); });
    document.addEventListener('fileguard:themechange', sync);
    sync();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', controls, {once:true}); else controls();
})();
