(() => {
  const applyBrand = () => {
    document.body.classList.add('hermes-nosso-skin');
    document.title = 'Hermes Nosso';

    const sidebar = document.getElementById('app-sidebar');
    if (!sidebar) return;

    const head = sidebar.firstElementChild;
    if (!head) return;

    const textNodes = head.querySelectorAll('p,span,div');
    for (const el of textNodes) {
      const txt = (el.textContent || '').replace(/\s+/g, ' ').trim().toLowerCase();
      if (txt === 'hermes agent') {
        el.innerHTML = 'HERMES<br>NOSSO';
        break;
      }
    }

    if (!head.querySelector('[data-hermes-nosso-badge]')) {
      const badge = document.createElement('span');
      badge.setAttribute('data-hermes-nosso-badge', '1');
      badge.textContent = 'CLOUD';
      const brandWrap = head.querySelector('div');
      if (brandWrap) brandWrap.appendChild(badge);
    }
  };

  applyBrand();
  const observer = new MutationObserver(() => applyBrand());
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();