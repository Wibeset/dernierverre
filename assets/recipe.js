/* Recipe pages: ml/oz and 1–12 glasses, formatted like the app (UserLibrary.swift).
   The page is rendered for 1 glass in ml, so it reads fine without JavaScript. */
(() => {
const decimal = v => (Math.round(v * 10) / 10).toString();
function fraction(v) {
  const q = Math.round(v * 4);
  if (q <= 0) return decimal(v);
  const whole = Math.floor(q / 4), frac = ['', '¼', '½', '¾'][q % 4];
  return whole === 0 ? frac : frac ? `${whole} ${frac}` : String(whole);
}
function fit(el, max, min = 16) {
  el.style.fontSize = '';
  let size = max ?? parseFloat(getComputedStyle(el).fontSize);
  el.style.fontSize = size + 'px';
  while (size > min && el.scrollWidth > el.clientWidth + 1) el.style.fontSize = (size -= 1) + 'px';
}
const fitAll = () => {
  document.querySelectorAll('.r-title').forEach(h => fit(h, null, 40));
  document.querySelectorAll('.tile h3').forEach(h => fit(h, 36));
  document.querySelectorAll('.fact .poster').forEach(h => fit(h, null, 12));
};
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
  document.getElementById('servings').textContent = `${servings} glass${servings > 1 ? 'es' : ''}`;
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
