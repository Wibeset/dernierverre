#!/usr/bin/env python3
"""Render link-preview and recipe images with headless Chrome (macOS: uses `sips` to convert to JPEG).

    python3 tools/images.py              # everything missing, both languages (--force to redo all)
    python3 tools/images.py negroni      # only these cocktails

Writes, for each language (en, fr):
    assets/og/<lang>/home.jpg, cocktails.jpg       1200×630, link previews
    assets/og/<lang>/<id>.jpg                      1200×630, link previews + Recipe schema
    assets/og/<lang>/<id>-1x1.jpg                  1200×1200, Recipe schema (Google wants several ratios)

Run after a cocktail's name, tagline, colour or ingredients change. Commit the output.
Icons and favicons are not generated: they come from the app's icon set (see README).
"""
import json, shutil, subprocess, sys, tempfile
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
recipes = json.loads((ROOT / 'data/recipes.json').read_text())
DATA = {l: json.loads((ROOT / f'data/{l}.json').read_text()) for l in ('en', 'fr')}
KICK = {'en': ('Cocktail recipe', 'Coming soon on iPhone', 'One more, perfectly mixed.', 'Every cocktail recipe.', 'recipes'),
        'fr': ('Recette de cocktail', 'Bientôt sur iPhone', 'Un dernier, parfaitement dosé.', 'Toutes les recettes.', 'recettes')}
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
.k{{font-size:{k}px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;display:flex;justify-content:space-between;align-items:center}}
.k img{{width:{icon}px;height:{icon}px;border-radius:{rad}px}}
.p{{font-stretch:62%;font-weight:900;text-transform:uppercase;line-height:.86;margin:0;overflow:hidden}}
.t{{font-size:{tl}px;font-weight:600;margin:18px 0 0;line-height:1.3}}
.r{{border-top:4px solid {ink};padding-top:18px;font-size:{r}px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;line-height:1.35}}
.sw{{display:flex;gap:10px}} .sw i{{width:44px;height:44px;border-radius:10px;border:3px solid {ink}}}
</style></head><body>{body}
<script>document.fonts.ready.then(()=>{{document.querySelectorAll('.p').forEach(el=>{{let s={max};el.style.fontSize=s+'px';
while(s>40&&(el.scrollWidth>el.clientWidth+1||el.scrollHeight>{maxh}))el.style.fontSize=(s-=2)+'px'}})}})</script></body></html>'''
ICON = (ROOT / 'assets/icons/icon-1024.png').as_uri()

def render(name, w, h, body, bg, max_title, max_h, k=22, tl=34, r=24, pad=64):
    src, png = TMP / f'{name}.html', TMP / f'{name}.png'
    src.write_text(PAGE.format(w=w, h=h, bg=bg, ink=ink_on(bg), body=body, pad=pad, k=k, tl=tl, r=r,
                               max=max_title, maxh=max_h, icon=k * 2.4, rad=k * .55))
    cmd = [CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
           f'--window-size={w},{h}', '--virtual-time-budget=4000', f'--screenshot={png}', src.as_uri()]
    for attempt in range(3):  # headless Chrome occasionally exits early; try again
        if subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0 and png.exists():
            return png
    raise SystemExit(f'Chrome failed to render {name}')

def jpg(png, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '82', str(png), '--out', str(dest)],
                   check=True, stdout=subprocess.DEVNULL)

FORCE = '--force' in sys.argv
only = {a for a in sys.argv[1:] if a != '--force'}
for lang in ('en', 'fr'):
    d, (kick, free, tagline, every, word) = DATA[lang], KICK[lang]
    out = ROOT / 'assets/og' / lang
    for i, r in enumerate(recipes, 1):
        if only and r['id'] not in only: continue  # pass 'home' to render only the home/list images
        if not FORCE and not only and (out / f'{r["id"]}-1x1.jpg').exists(): continue  # already rendered
        if lang == 'en':
            t = d['cocktails'][r['id']]; name, tl = t.get('name', r['name']), t['tagline']
        else:
            name, tl = r['name'], r['tagline']
        qty = lambda m: (f'{m["ml"]:g}'.replace('.', ',' if lang == 'fr' else '.') + ' ml ') if 'ml' in m else ''
        ings = ' · '.join(f'{qty(m)}{d["ingredients"][m["id"]].split(" (")[0]}' for m in r['ingredients'] if not m.get('optional'))
        head = f'<div class="k"><span>Dernier Verre · {kick}</span><span>N° {i:02d} / {len(recipes)}</span></div>'
        mid = f'<div><h1 class="p">{e(name)}</h1><p class="t">{e(tl)}</p></div>'
        jpg(render(f'{lang}-{r["id"]}-w', 1200, 630, f'{head}{mid}<div class="r">{e(ings)}</div>', r['color'], 220, 300), out / f'{r["id"]}.jpg')
        extra = f'<br>{e(d["labels"]["glass"][r["glass"]])} · {e(d["labels"]["method"][r["method"]])}'
        jpg(render(f'{lang}-{r["id"]}-s', 1200, 1200, f'{head}{mid}<div class="r">{e(ings)}{extra}</div>', r['color'], 300, 620,
                   k=26, tl=44, r=30, pad=80), out / f'{r["id"]}-1x1.jpg')
        print('✓', lang, r['id'])
    if not only or 'home' in only:
        sw = '<div class="sw">' + ''.join(f'<i style="background:{r["color"]}"></i>' for r in recipes[::3]) + '</div>'
        brand = f'<div class="k"><span style="display:flex;align-items:center;gap:16px"><img src="{ICON}" alt="">Dernier Verre</span><span>{free}</span></div>'
        jpg(render(f'{lang}-home', 1200, 630, f'{brand}<h1 class="p">{e(tagline)}</h1>{sw}', '#F4F2EC', 170, 340), out / 'home.jpg')
        brand = f'<div class="k"><span style="display:flex;align-items:center;gap:16px"><img src="{ICON}" alt="">Dernier Verre</span><span>{len(recipes)} {word}</span></div>'
        jpg(render(f'{lang}-cocktails', 1200, 630, f'{brand}<h1 class="p">{e(every)}</h1>{sw}', '#FF6B35', 170, 340), out / 'cocktails.jpg')
        print('✓', lang, 'home, cocktails')

shutil.rmtree(TMP, ignore_errors=True)
