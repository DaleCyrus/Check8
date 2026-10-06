(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const running = new Map();

  function enter(element) {
    if (!element) return;
    running.get(element)?.cancel();
    if (reducedMotion.matches || !element.animate) return;
    const animation = element.animate([
      { opacity: 0.6, transform: 'translateY(6px)' },
      { opacity: 1, transform: 'translateY(0)' }
    ], { duration: 220, easing: 'cubic-bezier(0.16, 1, 0.3, 1)' });
    running.set(element, animation);
    animation.finished.catch(() => {}).finally(() => {
      if (running.get(element) === animation) running.delete(element);
    });
  }

  reducedMotion.addEventListener('change', () => {
    if (reducedMotion.matches) running.forEach(animation => animation.cancel());
  });
  window.Check8Motion = { enter };

  document.addEventListener('DOMContentLoaded', () => {
    // Browsers without cross-document transitions still get an immediate entrance.
    if (!('onpagereveal' in window)) {
      enter(document.querySelector('.admin-content, #main-content'));
    }
    if (!window.gsap) return;
    window.gsap.matchMedia().add('(prefers-reduced-motion: no-preference)', () => {
      const artwork = document.querySelector('.auth-brand-art__sheet');
      if (artwork) window.gsap.from(artwork, {
        y: 10, rotation: -6, duration: 0.45, ease: 'power3.out'
      });
    });
  });
})();
