/* Shared by every page: FAQ opens one answer at a time, sections fade in on scroll. */
(() => {
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const faq = document.querySelectorAll('.faq details');
faq.forEach(d => d.addEventListener('toggle', () => { if (d.open) faq.forEach(o => o !== d && (o.open = false)); }));
const year = document.getElementById('year'); if (year) year.textContent = new Date().getFullYear();
const items = document.querySelectorAll('.rv');
if ('IntersectionObserver' in window && !reduced) {
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { rootMargin: '0px 0px -8% 0px' });
  items.forEach((el, i) => { el.style.transitionDelay = (i % 3) * 75 + 'ms'; io.observe(el); });
} else items.forEach(el => el.classList.add('in'));
})();
