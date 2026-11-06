#!/usr/bin/env python3
"""Render social/recipe images and icons with headless Chrome (macOS: uses `sips` to convert).

    python3 tools/images.py            # everything
    python3 tools/images.py negroni    # only these cocktails

Writes
    assets/og/home.jpg, assets/og/cocktails.jpg        1200×630, link previews
    assets/og/<id>.jpg                                  1200×630, link previews + Recipe schema
    assets/og/<id>-1x1.jpg                              1200×1200, Recipe schema (Google wants several ratios)

Run after build.py's data changes (new cocktail, new colour, new name). Commit the output.
"""
import json, shutil, subprocess, sys, tempfile
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
recipes = json.loads((ROOT / 'data/recipes.json').read_text())
en = json.loads((ROOT / 'data/en.json').read_text())
ING, L = en['ingredients'], en['labels']
OUT = ROOT / 'assets/og'
OUT.mkdir(parents=True, exist_ok=True)
TMP = Path(tempfile.mkdtemp(prefix='dv-img-'))

def ink_on(hex_):
    n = int(hex_[1:], 16)
    lin = lambda v: (v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4
    l = 0.2126 * lin(n >> 16 & 255) + 0.7152 * lin(n >> 8 & 255) + 0.0722 * lin(n & 255)
    return '#F4F2EC' if l <= 0.2 else '#0E0E0C'

PAGE = '''<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..900&display=block" rel="stylesheet">
<style>
*{{box-sizing:border-box}} html,body{{margin:0;width:{w}px;height:{h}px;overflow:hidden}}
body{{background:{bg};color:{ink};font-family:Archivo,sans-serif;padding:{pad}px;display:flex;flex-direction:column;justify-content:space-between}}
.k{{font-size:{k}px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;display:flex;justify-content:space-between}}
.p{{font-stretch:62%;font-weight:900;text-transform:uppercase;line-height:.86;margin:0;white-space:normal;overflow:hidden}}
.t{{font-size:{tl}px;font-weight:600;margin:18px 0 0;line-height:1.3}}
.r{{border-top:4px solid {ink};padding-top:18px;font-size:{r}px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;line-height:1.35}}
.sw{{display:flex;gap:10px}} .sw i{{width:44px;height:44px;border-radius:10px;border:3px solid {ink}}}
</style></head><body>{body}
<script>document.fonts.ready.then(()=>{{document.querySelectorAll('.p').forEach(el=>{{let s={max};el.style.fontSize=s+'px';
while(s>40&&(el.scrollWidth>el.clientWidth+1||el.scrollHeight>{maxh}))el.style.fontSize=(s-=2)+'px'}})}})</script></body></html>'''

def render(name, w, h, body, bg, max_title=230, max_h=None, k=22, tl=34, r=24, pad=64):
    html = PAGE.format(w=w, h=h, bg=bg, ink=ink_on(bg), body=body, pad=pad, k=k, tl=tl, r=r,
                       max=max_title, maxh=max_h or int(h * .55))
    src, png = TMP / f'{name}.html', TMP / f'{name}.png'
    src.write_text(html)
    subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', f'--window-size={w},{h}',
                    '--virtual-time-budget=4000', f'--screenshot={png}', src.as_uri()],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return png

def to_jpg(png, dest):
    subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '82', str(png), '--out', str(dest)],
                   check=True, stdout=subprocess.DEVNULL)

def qty(m):
    if 'ml' in m: return f'{m["ml"]:g} ml'
    return ''

only = set(sys.argv[1:])
names = {r['id']: en['cocktails'][r['id']].get('name', r['name']) for r in recipes}

for i, r in enumerate(recipes, 1):
    if only and r['id'] not in only: continue
    t = en['cocktails'][r['id']]
    name = names[r['id']]
    ings = ' · '.join(f'{qty(m)} {ING[m["id"]].split(" (")[0]}'.strip() for m in r['ingredients'] if not m.get('optional'))
    head = f'<div class="k"><span>Dernier Verre · Cocktail recipe</span><span>N° {i:02d} / {len(recipes)}</span></div>'
    body = f'{head}<div><h1 class="p">{e(name)}</h1><p class="t">{e(t["tagline"])}</p></div><div class="r">{e(ings)}</div>'
    to_jpg(render(f'{r["id"]}-w', 1200, 630, body, r['color'], 220, 300), OUT / f'{r["id"]}.jpg')
    body = f'{head}<div><h1 class="p">{e(name)}</h1><p class="t">{e(t["tagline"])}</p></div><div class="r">{e(ings)}<br>{e(L["glass"][r["glass"]])} · {e(L["method"][r["method"]])}</div>'
    to_jpg(render(f'{r["id"]}-s', 1200, 1200, body, r['color'], 300, 620, k=26, tl=44, r=30, pad=80), OUT / f'{r["id"]}-1x1.jpg')
    print('✓', r['id'])

if not only:
    swatches = '<div class="sw">' + ''.join(f'<i style="background:{r["color"]}"></i>' for r in recipes[::3]) + '</div>'
    body = f'<div class="k"><span>Dernier Verre</span><span>Free on iPhone</span></div><h1 class="p">One more, perfectly mixed.</h1>{swatches}'
    to_jpg(render('home', 1200, 630, body, '#F4F2EC', 170, 340), OUT / 'home.jpg')
    body = f'<div class="k"><span>Dernier Verre</span><span>{len(recipes)} recipes</span></div><h1 class="p">Every cocktail recipe.</h1>{swatches}'
    to_jpg(render('cocktails', 1200, 630, body, '#FF6B35', 170, 340), OUT / 'cocktails.jpg')

    print('✓ home, cocktails')

shutil.rmtree(TMP, ignore_errors=True)
