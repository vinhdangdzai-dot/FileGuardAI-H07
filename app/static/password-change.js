(() => {
  'use strict';
  const buttons = [...document.querySelectorAll('[data-reveal]')];
  function hide(button) {
    document.getElementById(button.dataset.reveal).type = 'password';
    button.setAttribute('aria-pressed','false');
    button.textContent = 'Hiện';
    button.setAttribute('aria-label','Hiện '+document.querySelector('label[for="'+button.dataset.reveal+'"]').textContent.toLowerCase());
  }
  buttons.forEach(button => {
    button.hidden = false;
    button.addEventListener('click', () => {
      const input = document.getElementById(button.dataset.reveal);
      if (input.type === 'text') hide(button);
      else {
        input.type = 'text';button.textContent = 'Ẩn';button.setAttribute('aria-pressed','true');
        button.setAttribute('aria-label','Ẩn '+document.querySelector('label[for="'+input.id+'"]').textContent.toLowerCase());
      }
    });
  });
  window.addEventListener('pageshow', () => buttons.forEach(hide));
})();
