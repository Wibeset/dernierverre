/* Recipe pages: ml/oz and 1–12 glasses, formatted like the app (UserLibrary.swift).
   The page is rendered for 1 glass in ml, so it reads fine without JavaScript. */
(() => {
const sep = ['fr', 'es'].includes(document.documentElement.lang) ? ',' : '.';
const decimal = v => (Math.round(v * 10) / 10).toString().replace('.', sep);
function fraction(v) {
  const q = Math.round(v * 4);
  if (q <= 0) return decimal(v);
  const whole = Math.floor(q / 4), frac = ['', '¼', '½', '¾'][q % 4];
  return whole === 0 ? frac : frac ? `${whole} ${frac}` : String(whole);
}
/* Shrink poster titles until every word fits (SwiftUI's minimumScaleFactor).
   Widths are only read on the frame after a change, once the browser has laid the page out itself,
   so measuring never forces a synchronous layout (PageSpeed: forced reflow). jobs: [[el, max|null, min]] */
const later = f => requestAnimationFrame(() => setTimeout(f));
function fit(jobs) {
  jobs = jobs.filter(([el]) => el);
  jobs.forEach(([el, max]) => { const want = max == null ? '' : max + 'px'; if (el.style.fontSize !== want) el.style.fontSize = want; });
  const measure = () => {
    const m = jobs.map(([el]) => [el.scrollWidth, el.clientWidth, parseFloat(getComputedStyle(el).fontSize)]);
    jobs = jobs.filter(([el, , min], i) => {
      const [sw, cw, size] = m[i];
      if (sw <= cw + 1 || size <= min) return false;
      el.style.fontSize = Math.max(min, Math.min(size - 1, Math.floor(size * cw / sw))) + 'px';
      return true;
    });
    if (jobs.length) later(measure);   // check the ones that shrank, next frame
  };
  later(measure);
}
const fitAll = () => fit([
  ...[...document.querySelectorAll('.r-title')].map(h => [h, null, 40]),
  ...[...document.querySelectorAll('.tile h3')].map(h => [h, 36, 16]),
  ...[...document.querySelectorAll('.fact .poster')].map(h => [h, null, 12]),
]);
(document.fonts ? document.fonts.ready : Promise.resolve()).then(fitAll);
let rz; addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(fitAll, 120); });

const list = document.querySelector('.ing-list');
if (!list) return;
let servings = 1;
let unit = 'ml';
try { if (localStorage.getItem('dv-unit') === 'oz') unit = 'oz'; } catch {}

function render() {
  list.querySelectorAll('[data-ml]').forEach(el => {
    const t = parseFloat(el.dataset.ml) * servings;
    el.textContent = unit === 'ml' ? `${decimal(t)} ml` : `${fraction(t / 30)} oz`;
  });
  list.querySelectorAll('[data-count]').forEach(el => {
    const t = parseFloat(el.dataset.count) * servings;
    el.textContent = `${fraction(t)} ${t > 1 ? el.dataset.many : el.dataset.one}`;
  });
  const sv = document.getElementById('servings');
  sv.textContent = `${servings} ${servings > 1 ? sv.dataset.many : sv.dataset.one}`;
  document.querySelectorAll('[data-unit]').forEach(b => b.setAttribute('aria-pressed', b.dataset.unit === unit));
  document.querySelector('[data-step="-1"]').disabled = servings <= 1;
  document.querySelector('[data-step="1"]').disabled = servings >= 12;
}
document.querySelectorAll('[data-unit]').forEach(b => b.addEventListener('click', () => {
  unit = b.dataset.unit;
  try { localStorage.setItem('dv-unit', unit); } catch {}
  render();
}));
document.querySelectorAll('[data-step]').forEach(b => b.addEventListener('click', () => {
  servings = Math.min(12, Math.max(1, servings + Number(b.dataset.step)));
  render();
}));
render();
})();
