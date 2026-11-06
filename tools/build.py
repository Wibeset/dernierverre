#!/usr/bin/env python3
"""Build the static site for GitHub Pages (https://dernierverre.app).

    python3 tools/build.py

Reads data/recipes.json (extracted from the app, see extract.py) and data/en.json
(English copy), then writes:

    assets/data.js              recipe data for the home page's scripts
    index.html                  library tiles + counts, between <!-- build:… --> markers
    cocktails/index.html        every recipe, grouped by spirit
    cocktails/<id>/index.html   one page per cocktail
    404.html, sitemap.xml, robots.txt, CNAME, .nojekyll

Only the standard library; no dependencies. Run it again after changing either JSON file.
"""
import html, json, re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = 'https://dernierverre.app'
APP_STORE = '#download'  # TODO: the App Store URL, once the app is published

recipes = json.loads((ROOT / 'data/recipes.json').read_text())
en = json.loads((ROOT / 'data/en.json').read_text())
L, UNITS, ING = en['labels'], en['units'], en['ingredients']

missing = [c['id'] for c in recipes if c['id'] not in en['cocktails']]
if missing: raise SystemExit(f'data/en.json has no English copy for: {", ".join(missing)}')

e = lambda s: html.escape(str(s), quote=True)

def ink_on(hex_):
    """Theme.isDark from the app: relative luminance ≤ 0.2 → paper ink."""
    n = int(hex_[1:], 16)
    def lin(v):
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    l = 0.2126 * lin(n >> 16 & 255) + 0.7152 * lin(n >> 8 & 255) + 0.0722 * lin(n & 255)
    return '#F4F2EC' if l <= 0.2 else '#0E0E0C'

# ---------- merge the two sources into one English view of each cocktail ----------
C = []
for i, r in enumerate(recipes):
    t = en['cocktails'][r['id']]
    if len(t['steps']) != len(r['steps']):
        raise SystemExit(f"{r['id']}: {len(r['steps'])} steps in the app, {len(t['steps'])} in en.json")
    C.append({**r, 'n': i + 1, 'name': t.get('name', r['name']), 'tagline': t['tagline'],
              'description': t['description'], 'steps': t['steps'], 'garnish': t['garnish'],
              'ink': ink_on(r['color'])})
BY_BASE = {}
for c in C: BY_BASE.setdefault(c['base'], []).append(c)

# ---------- quantities, formatted like the app (UserLibrary.swift) ----------
def decimal(v): return f'{v:.1f}'.rstrip('0').rstrip('.')
def fraction(v):
    q = round(v * 4)
    if q <= 0: return decimal(v)
    whole, frac = divmod(q, 4)
    frac = ['', '¼', '½', '¾'][frac]
    return frac if whole == 0 else (str(whole) if not frac else f'{whole} {frac}')
def qty(m, servings=1, unit='ml'):
    if 'ml' in m:
        t = m['ml'] * servings
        return f'{decimal(t)} ml' if unit == 'ml' else f'{fraction(t / 30)} oz'
    if 'count' in m:
        t = m['count'] * servings
        one, many = UNITS[m['unit']]
        return f'{fraction(t)} {many if t > 1 else one}'
    if m.get('top'): return UNITS['top']
    return UNITS.get(m['text'], m['text'])

def qty_attrs(m):
    """What recipe.js needs to re-format a quantity for other servings/units."""
    if 'ml' in m: return f' data-ml="{m["ml"]}"'
    if 'count' in m:
        one, many = UNITS[m['unit']]
        return f' data-count="{m["count"]}" data-one="{e(one)}" data-many="{e(many)}"'
    return ''

# ---------- shared page parts ----------
APPLE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16.37 12.6c-.02-2.3 1.88-3.4 1.96-3.46a4.24 4.24 0 0 0-3.33-1.8c-1.42-.15-2.77.84-3.49.84-.72 0-1.83-.82-3-.8a4.46 4.46 0 0 0-3.77 2.29c-1.61 2.79-.41 6.92 1.16 9.18.77 1.1 1.68 2.35 2.88 2.3 1.16-.04 1.6-.74 3-.74s1.79.74 3.01.72c1.25-.02 2.04-1.12 2.8-2.23a9.8 9.8 0 0 0 1.27-2.6 4.04 4.04 0 0 1-2.46-3.7zM14.05 5.86A4.03 4.03 0 0 0 15 2.9a4.1 4.1 0 0 0-2.66 1.37 3.84 3.84 0 0 0-.97 2.86 3.4 3.4 0 0 0 2.68-1.27z"/></svg>'

def head(title, desc, path, up, extra='', color=None):
    theme = color or '#F4F2EC'
    style = f' style="--bg:{color};--ink:{ink_on(color)}"' if color else ''
    return f'''<!doctype html>
<html lang="en"{style}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="theme-color" content="{theme}">
<link rel="canonical" href="{SITE}{path}">
<meta property="og:url" content="{SITE}{path}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Dernier Verre">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23FF6B35'/%3E%3Cpath d='M16 18h32L34 34v12h7v4H23v-4h7V34z' fill='%230E0E0C'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{up}assets/site.css">
{extra}</head>
<body>
<script>document.documentElement.classList.add('js')</script>
<header class="site surface">
  <div class="col pad">
    <a href="{up}" class="logo poster" aria-label="Dernier Verre — home"><i aria-hidden="true"></i>Dernier Verre</a>
    <nav class="main" aria-label="Sections">
      <a href="{up}#how">How it works</a>
      <a href="{up}#bar">My bar</a>
      <a href="{up}#features">Features</a>
      <a href="{up}cocktails/">Recipes</a>
      <a href="{up}#faq">FAQ</a>
    </nav>
    <a class="pill" href="{up}#download">Get the app</a>
  </div>
</header>
'''

def foot(up, scripts=('site.js',)):
    js = ''.join(f'<script src="{up}assets/{s}"></script>\n' for s in scripts)
    return f'''<footer class="surface">
  <div class="col pad">
    <div>
      <a href="{up}" class="logo poster">Dernier Verre</a>
      <p class="body muted" style="margin-top:10px">One more, perfectly mixed.</p>
    </div>
    <nav aria-label="Footer">
      <a href="{up}#how">How it works</a>
      <a href="{up}#bar">My bar</a>
      <a href="{up}#features">Features</a>
      <a href="{up}cocktails/">All recipes</a>
      <a href="{up}#faq">FAQ</a>
    </nav>
    <div class="legal">
      <span class="legal-left"><span>© <span id="year">{date.today().year}</span> Dernier Verre</span> <span class="credit">Made with <span class="heartbeat" aria-hidden="true"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M11.645 20.91l-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.36 2.25 12.174 2.25 8.25 2.25 5.322 4.714 3 7.688 3A5.5 5.5 0 0112 5.052 5.5 5.5 0 0116.313 3c2.973 0 5.437 2.322 5.437 5.25 0 3.925-2.438 7.111-4.739 9.256a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.219l-.022.012-.007.004-.003.001a.752.752 0 01-.704 0l-.003-.001z"/></svg></span><span class="sr">love</span> by <a href="https://wibeset.ca" rel="noopener">Wibeset</a> in Quebec <span aria-hidden="true">🇨🇦</span></span></span>
      <span>Please drink responsibly. Never drink and drive.</span>
    </div>
  </div>
</footer>
{js}</body>
</html>
'''

def tile(c, up):
    ings = ' · '.join(re.sub(r'\s*\(.*\)$', '', ING[m['id']]) for m in c['ingredients'] if not m.get('optional'))
    return (f'<a class="tile" href="{up}cocktails/{c["id"]}/" data-base="{c["base"]}" style="--bg:{c["color"]};--ink:{c["ink"]}">'
            f'<p class="kicker">N° {c["n"]:02d} · {e(L["base"][c["base"]])}</p>'
            f'<div><h3 class="poster">{e(c["name"])}</h3><p class="ing">{e(ings)}</p></div></a>')

def write(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

# ---------- assets/data.js ----------
data = {
    'cocktails': [{'id': c['id'], 'name': c['name'], 'tagline': c['tagline'], 'base': c['base'], 'color': c['color'],
                   'ing': [[m['id'], m.get('ml'), bool(m.get('optional'))] for m in c['ingredients']]} for c in C],
    'ingredients': ING,
    'base': L['base'],
}
write('assets/data.js', '/* Generated by tools/build.py — do not edit. */\nwindow.DV = '
      + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')

# ---------- index.html: library tiles and counts ----------
index = (ROOT / 'index.html').read_text()
tiles = '\n'.join(tile(c, '') for c in C) + f'''
<div class="tile end"><h3 class="poster">That’s all.</h3><p class="body">Can’t choose? Let chance pick.</p><button type="button" class="pill" id="surprise">Surprise me →</button></div>'''
index = re.sub(r'(<!-- build:library -->).*?(<!-- /build:library -->)', lambda m: f'{m[1]}\n{tiles}\n{m[2]}', index, flags=re.S)
index = re.sub(r'(<!-- build:count -->).*?(<!-- /build:count -->)', lambda m: f'{m[1]}{len(C)}{m[2]}', index)
(ROOT / 'index.html').write_text(index)

# ---------- one page per cocktail ----------
def related(c):
    same = [x for x in BY_BASE[c['base']] if x is not c]
    if len(same) < 4:  # top up with neighbours from the library so the row is never thin
        i = C.index(c)
        same += [x for x in C[i + 1:] + C[:i] if x not in same and x is not c][:4 - len(same)]
    return same[:6]

for i, c in enumerate(C):
    up = '../../'
    path = f'/cocktails/{c["id"]}/'
    base, glass = L['base'][c['base']], L['glass'][c['glass']]
    prev, nxt = C[i - 1], C[(i + 1) % len(C)]
    desc = f'How to make a {c["name"]}: {c["tagline"].lower()}. ' + ' '.join(c['description'].split('. ')[:1]).rstrip('.') + '.'
    ld = {
        '@context': 'https://schema.org', '@type': 'Recipe',
        'name': c['name'], 'description': c['description'],
        'recipeCategory': 'Cocktail', 'keywords': ', '.join([base] + [L['flavors'][f] for f in c['flavors']]),
        'recipeYield': '1 drink',
        'recipeIngredient': [f'{qty(m)} {ING[m["id"]]}'.strip() for m in c['ingredients']],
        'recipeInstructions': [{'@type': 'HowToStep', 'text': s} for s in c['steps']],
        'url': SITE + path,
    }
    extra = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n'

    facts = ''.join(f'<div class="fact"><p class="kicker">{k}</p><p class="poster">{e(v)}</p></div>' for k, v in [
        ('Strength', L['strength'][c['strength']]), ('Difficulty', L['difficulty'][c['difficulty']]), ('Method', L['method'][c['method']])])
    tags = ''.join(f'<span class="tagpill">{o[0]} {e(o[1])}</span>' for o in (L['occasions'][x] for x in c['occasions']))
    tags += ''.join(f'<span class="tagpill">{e(L["flavors"][x])}</span>' for x in c['flavors'])
    ings = ''.join(
        f'<li class="ing-row"><span><span class="ing-name">{e(ING[m["id"]])}</span>'
        + ('<span class="opt">optional</span>' if m.get('optional') else '')
        + f'</span><span class="poster q"{qty_attrs(m)}>{e(qty(m))}</span></li>' for m in c['ingredients'])
    steps = ''.join(f'<li><span class="poster sn">{j:02d}</span><span>{e(s)}</span></li>' for j, s in enumerate(c['steps'], 1))
    garnish = f'<p class="garnish"><b>Garnish</b> {e(c["garnish"])}</p>' if c['garnish'] else ''
    more = ''.join(tile(x, up) for x in related(c))
    more_title = f'More with {base.lower()}' if len(BY_BASE[c['base']]) > 1 else 'You might also like'

    page = head(f'{c["name"]} recipe — Dernier Verre', desc, path, up, extra, c['color']) + f'''
<main class="recipe">
  <div class="col pad r-nav">
    <a class="chip" href="{up}cocktails/">← All recipes</a>
    <span class="kicker">N° {c["n"]:02d} / {len(C)}</span>
  </div>

  <div class="col pad">
    <section class="r-poster">
      <p class="kicker">{e(base)} · {e(glass)}</p>
      <h1 class="poster r-title">{e(c["name"])}</h1>
      <p class="lead">{e(c["tagline"])}</p>
      <div class="facts-row">{facts}</div>
      <div class="tags">{tags}</div>
    </section>
    <p class="r-desc">{e(c["description"])}</p>
  </div>

  <div class="col pad r-grid">
    <section class="r-ing" aria-labelledby="ing-h">
      <div class="r-ing-head">
        <h2 class="poster" id="ing-h">Ingredients</h2>
        <div class="seg" role="group" aria-label="Units">
          <button type="button" data-unit="ml" aria-pressed="true">ml</button><button type="button" data-unit="oz" aria-pressed="false">oz</button>
        </div>
      </div>
      <div class="servings">
        <span class="poster" id="servings" aria-live="polite">1 glass</span>
        <button type="button" class="circle" data-step="-1" aria-label="Fewer glasses">−</button>
        <button type="button" class="circle" data-step="1" aria-label="More glasses">+</button>
      </div>
      <ul class="ing-list">{ings}</ul>
      {garnish}
    </section>

    <section class="r-steps" aria-labelledby="steps-h">
      <h2 class="poster" id="steps-h">Preparation</h2>
      <ol class="step-list">{steps}</ol>
    </section>
  </div>

  <section class="col pad">
    <div class="r-app">
      <div>
        <h2 class="poster">Keep it in your pocket.</h2>
        <p class="body">In Dernier Verre, tap an ingredient to add it to your bar — the app shows every cocktail you can make tonight. Free on iPhone.</p>
      </div>
      <a class="pill" href="{APP_STORE if APP_STORE != '#download' else up + '#download'}" data-appstore>{APPLE} Download free</a>
    </div>
  </section>

  <section class="col r-more" aria-labelledby="more-h">
    <div class="pad r-more-head"><h2 class="kicker" id="more-h">{e(more_title)}</h2><a class="kicker" href="{up}cocktails/">All {len(C)} recipes →</a></div>
    <div class="lib">{more}</div>
  </section>

  <nav class="col pad r-pn" aria-label="Previous and next recipe">
    <a href="{up}cocktails/{prev["id"]}/"><span class="kicker">← Previous</span><span class="poster">{e(prev["name"])}</span></a>
    <a href="{up}cocktails/{nxt["id"]}/" class="next"><span class="kicker">Next →</span><span class="poster">{e(nxt["name"])}</span></a>
  </nav>
</main>
''' + foot(up, ('site.js', 'recipe.js'))
    write(f'cocktails/{c["id"]}/index.html', page)

# ---------- all recipes, grouped by spirit ----------
up = '../'
groups = ''.join(f'''
  <section class="col r-group" id="{k}" aria-labelledby="g-{k}">
    <div class="pad r-more-head"><h2 class="kicker" id="g-{k}">{e(L["base"][k])}</h2><span class="kicker">{len(BY_BASE[k])}</span></div>
    <div class="lib">{"".join(tile(c, up) for c in BY_BASE[k])}</div>
  </section>''' for k in L['base'] if k in BY_BASE)
jump = ''.join(f'<a class="chip" href="#{k}">{e(L["base"][k])}</a>' for k in L['base'] if k in BY_BASE)
write('cocktails/index.html', head(f'All {len(C)} cocktail recipes — Dernier Verre',
      f'{len(C)} classic cocktail recipes with exact measures in ml and oz: from the Negroni to the Caesar, including alcohol-free drinks.',
      '/cocktails/', up) + f'''
<main>
  <section class="col pad r-hero">
    <p class="kicker">The library · {len(C)} recipes</p>
    <h1 class="poster r-title list-title">Every recipe.</h1>
    <p class="lead">Classics, modern classics and alcohol-free drinks, each with exact measures and step-by-step preparation.</p>
    <div class="lib-filters jump">{jump}</div>
  </section>
  {groups}
</main>
''' + foot(up, ('site.js', 'recipe.js')))

# ---------- 404 ----------
write('404.html', head('Last call — Dernier Verre', 'This page has been cleared from the bar.', '/404.html', '/') + '''
<main class="col pad r-hero" style="min-height:60vh">
  <p class="kicker">Error 404</p>
  <h1 class="poster r-title">Last call.</h1>
  <p class="lead">This glass is empty — the page you’re looking for doesn’t exist.</p>
  <p><a class="pill" href="/">Back to the bar</a> <a class="pill ghost" href="/cocktails/">All recipes</a></p>
</main>
''' + foot('/'))

# ---------- sitemap, robots, GitHub Pages ----------
urls = ['/', '/cocktails/'] + [f'/cocktails/{c["id"]}/' for c in C]
write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
      + ''.join(f'  <url><loc>{SITE}{u}</loc></url>\n' for u in urls) + '</urlset>\n')
write('robots.txt', f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n')
write('CNAME', 'dernierverre.app\n')
write('.nojekyll', '')
print(f'Built {len(C)} recipe pages, cocktails/index.html, 404.html, sitemap.xml ({len(urls)} URLs).')
