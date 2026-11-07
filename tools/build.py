#!/usr/bin/env python3
"""Build the static site for GitHub Pages (https://dernierverre.app), in English and French.

    python3 tools/build.py

Sources
    src/home.html          home page body, with {{key}} placeholders
    data/recipes.json      recipes extracted from the app (French text, quantities, colours) — see extract.py
    data/en.json           English recipe copy and labels
    data/fr.json           French descriptions and labels (names, taglines, steps come from the app)
    data/ui.json           interface strings, both languages

Output (English at the root, French under /fr/)
    index.html, fr/index.html                      home
    cocktails/index.html, fr/cocktails/index.html  all recipes
    cocktails/<id>/, fr/cocktails/<id>/            one page per cocktail
    assets/data.en.js, assets/data.fr.js           data for the home page scripts
    404.html, sitemap.xml, robots.txt, llms.txt, site.webmanifest, CNAME, .nojekyll

Images (assets/og/) are rendered separately by tools/images.py. Standard library only.
"""
import html, json, re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = 'https://dernierverre.app'
APP_STORE = None  # the App Store URL once the app is published; until then buttons say "coming soon"
LANGS = ('en', 'fr')
PREFIX = {'en': '', 'fr': 'fr/'}

recipes = json.loads((ROOT / 'data/recipes.json').read_text())
DATA = {'en': json.loads((ROOT / 'data/en.json').read_text()), 'fr': json.loads((ROOT / 'data/fr.json').read_text())}
UI = json.loads((ROOT / 'data/ui.json').read_text())
HOME = (ROOT / 'src/home.html').read_text()
TODAY = date.today().isoformat()

e = lambda s: html.escape(str(s), quote=True)

for r in recipes:
    if r['id'] not in DATA['en']['cocktails']: raise SystemExit(f'data/en.json: no English copy for {r["id"]}')
    if r['id'] not in DATA['fr']['cocktails']: raise SystemExit(f'data/fr.json: no French description for {r["id"]}')
    if len(DATA['en']['cocktails'][r['id']]['steps']) != len(r['steps']):
        raise SystemExit(f'{r["id"]}: {len(r["steps"])} steps in the app, {len(DATA["en"]["cocktails"][r["id"]]["steps"])} in en.json')

def lum(hex_):
    n = int(hex_[1:], 16)
    lin = lambda v: (v / 255) / 12.92 if v / 255 <= 0.03928 else (((v / 255) + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(n >> 16 & 255) + 0.7152 * lin(n >> 8 & 255) + 0.0722 * lin(n & 255)

def ink_on(hex_):
    """Theme.isDark from the app: relative luminance ≤ 0.2 → paper ink, else chrome ink.
    The web also needs WCAG AA (4.5:1) for small text: on the few mid-tones where neither
    passes (Americano, Oaxaca old fashioned), fall back to pure black or white."""
    l = lum(hex_)
    ink = '#F4F2EC' if l <= 0.2 else '#0E0E0C'
    contrast = lambda a, b: (max(a, b) + .05) / (min(a, b) + .05)
    if contrast(l, lum(ink)) >= 4.5: return ink
    return '#000000' if contrast(l, 0) >= contrast(l, 1) else '#FFFFFF'

# ---------- one localized view of each cocktail ----------
def cocktails(lang):
    d, out = DATA[lang], []
    for i, r in enumerate(recipes, 1):
        if lang == 'en':
            t = d['cocktails'][r['id']]
            text = dict(name=t.get('name', r['name']), tagline=t['tagline'], description=t['description'], steps=t['steps'], garnish=t['garnish'])
        else:
            text = dict(name=r['name'], tagline=r['tagline'], description=d['cocktails'][r['id']], steps=r['steps'], garnish=r['garnish'])
        out.append({**r, **text, 'n': i, 'ink': ink_on(r['color'])})
    return out
C = {lang: cocktails(lang) for lang in LANGS}

# ---------- quantities, formatted like the app (UserLibrary.swift) ----------
def decimal(v, lang): return f'{v:.1f}'.rstrip('0').rstrip('.').replace('.', ',' if lang == 'fr' else '.')
def fraction(v, lang):
    q = round(v * 4)
    if q <= 0: return decimal(v, lang)
    whole, frac = divmod(q, 4)
    frac = ['', '¼', '½', '¾'][frac]
    return frac if whole == 0 else (str(whole) if not frac else f'{whole} {frac}')
def qty(m, lang, servings=1, unit='ml'):
    U = DATA[lang]['units']
    if 'ml' in m:
        t = m['ml'] * servings
        return f'{decimal(t, lang)} ml' if unit == 'ml' else f'{fraction(t / 30, lang)} oz'
    if 'count' in m:
        t = m['count'] * servings
        one, many = U[m['unit']]
        return f'{fraction(t, lang)} {many if t > 1 else one}'
    if m.get('top'): return U['top']
    return U.get(m['text'], m['text'])
def qty_attrs(m, lang):
    """What recipe.js needs to re-format a quantity for other servings/units."""
    if 'ml' in m: return f' data-ml="{m["ml"]}"'
    if 'count' in m:
        one, many = DATA[lang]['units'][m['unit']]
        return f' data-count="{m["count"]}" data-one="{e(one)}" data-many="{e(many)}"'
    return ''

# ---------- the one-sentence answer ("What's in a Negroni?") ----------
BRANDS = {'campari', 'aperol', 'chartreuse', 'amaro', 'angostura', 'peychaud', 'clamato', 'tabasco', 'worcestershire'}
def ing_lower(i, lang):
    name = re.sub(r'\s*\(.*\)$', '', DATA[lang]['ingredients'][i])
    if i in BRANDS and not (lang == 'fr' and i == 'worcestershire'): return name
    return name[0].lower() + name[1:]
def de(word):  # French partitive: "de gin", "d’Aperol"
    return ('d’' if word[0].lower() in 'aeiouyhéèêâîôû' else 'de ') + word
def phrase(m, lang):
    name = ing_lower(m['id'], lang)
    if 'count' in m:
        q = qty(m, lang)
        unit = DATA[lang]['units'][m['unit']][0]
        if name.lower().startswith(unit.lower()): return f'{fraction(m["count"], lang)} {name}'
        return f'{q} {de(name)}' if lang == 'fr' else f'{q} of {name}'
    if 'text' in m:
        if m['text'] == '2 c. à thé': return f'2 c. à thé {de(name)}' if lang == 'fr' else f'2 tsp {name}'
        return None  # "to rim the glass" and friends read better in the list than in a sentence
    return f'{qty(m, lang)} {de(name)}' if lang == 'fr' else f'{qty(m, lang)} {name}'
def summary(c, lang):
    u = UI[lang]
    parts = [p for m in c['ingredients'] if not m.get('optional') and not m.get('top') for p in [phrase(m, lang)] if p]
    lst = parts[0] if len(parts) == 1 else ', '.join(parts[:-1]) + f' {u["and"]} ' + parts[-1]
    tops = [ing_lower(m['id'], lang) for m in c['ingredients'] if m.get('top')]
    if tops: lst += u['summary_top'].format(x=de(tops[0]) if lang == 'fr' else tops[0])
    a = 'An' if c['name'][0].upper() in 'AEIOU' else 'A'
    first = u['summary_with'].format(a=a, name=c['name'], list=lst)
    return first, u['summary_method'].format(method=u['method_sentence'][c['method']], glass=u['glass_article'][c['glass']])
def meta_desc(c, lang):
    first, second = summary(c, lang)
    full = f'{first} {second}'
    if len(full) <= 160: return full
    return first if len(first) <= 160 else first[:157].rsplit(' ', 1)[0] + '…'

# ---------- shared page parts ----------
APPLE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16.37 12.6c-.02-2.3 1.88-3.4 1.96-3.46a4.24 4.24 0 0 0-3.33-1.8c-1.42-.15-2.77.84-3.49.84-.72 0-1.83-.82-3-.8a4.46 4.46 0 0 0-3.77 2.29c-1.61 2.79-.41 6.92 1.16 9.18.77 1.1 1.68 2.35 2.88 2.3 1.16-.04 1.6-.74 3-.74s1.79.74 3.01.72c1.25-.02 2.04-1.12 2.8-2.23a9.8 9.8 0 0 0 1.27-2.6 4.04 4.04 0 0 1-2.46-3.7zM14.05 5.86A4.03 4.03 0 0 0 15 2.9a4.1 4.1 0 0 0-2.66 1.37 3.84 3.84 0 0 0-.97 2.86 3.4 3.4 0 0 0 2.68-1.27z"/></svg>'
HEART = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M11.645 20.91l-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.36 2.25 12.174 2.25 8.25 2.25 5.322 4.714 3 7.688 3A5.5 5.5 0 0112 5.052 5.5 5.5 0 0116.313 3c2.973 0 5.437 2.322 5.437 5.25 0 3.925-2.438 7.111-4.739 9.256a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.219l-.022.012-.007.004-.003.001a.752.752 0 01-.704 0l-.003-.001z"/></svg>'
ORG = {'@type': 'Organization', '@id': f'{SITE}/#wibeset', 'name': 'Wibeset', 'url': 'https://wibeset.ca'}

def store_button(label, cls='pill'):
    """App Store button: a link once APP_STORE is set, a plain 'coming soon' pill before that."""
    if APP_STORE: return f'<a class="{cls}" href="{APP_STORE}" data-appstore>{APPLE} {label}</a>'
    return f'<span class="{cls} soon">{APPLE} {label}</span>'

# Styles are inlined and the font is self-hosted so nothing blocks the first paint (PageSpeed: render-blocking requests).
def minify_css(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    css = re.sub(r'\s+', ' ', css)
    return re.sub(r'\s*([{};,])\s*', r'\1', css).replace(';}', '}').strip()

CSS = minify_css((ROOT / 'assets/site.css').read_text())
FONT_FACE = ("@font-face{{font-family:Archivo;font-style:normal;font-weight:400 900;font-stretch:62% 125%;font-display:swap;"
             "src:url({up}assets/fonts/archivo-{subset}.woff2) format('woff2');unicode-range:{range}}}")
FONT_RANGES = {
    'latin-ext': 'U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C4,U+2113,U+2C60-2C7F,U+A720-A7FF',
    'latin': 'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD',
}
def fonts(up):
    return ''.join(FONT_FACE.format(up=up, subset=k, range=v) for k, v in FONT_RANGES.items())

def up_for(path):
    """Relative prefix from a page's URL path back to the site root."""
    return '../' * (path.strip('/').count('/') + 1) if path.strip('/') else ''

def head(lang, title, desc, path, alt, extra=(), color=None, image=None, noindex=False, base=None):
    """alt: {'en': path, 'fr': path} — the same page in each language."""
    u = UI[lang]
    up = base if base is not None else up_for(path)
    theme = color or '#F4F2EC'
    style = f' style="--bg:{color};--ink:{ink_on(color)}"' if color else ''
    image = image or f'{SITE}/assets/og/{lang}/home.jpg'
    links = '' if noindex else (f'<link rel="canonical" href="{SITE}{path}">\n'
             + ''.join(f'<link rel="alternate" hreflang="{l}" href="{SITE}{p}">\n' for l, p in alt.items())
             + f'<link rel="alternate" hreflang="x-default" href="{SITE}{alt["en"]}">\n')
    ld = ''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>\n' for x in extra)
    other = 'fr' if lang == 'en' else 'en'
    cur = lambda l: ' aria-current="true"' if l == lang else ''
    switch = (f'<span class="langs"><a href="{up}{alt["en"].lstrip("/") or "./"}" hreflang="en" lang="en"{cur("en")}>EN</a>'
              f'<span aria-hidden="true">/</span><a href="{up}{alt["fr"].lstrip("/")}" hreflang="fr" lang="fr"{cur("fr")}>FR</a></span>')
    home = up + PREFIX[lang]
    kind = 'article' if path.count('/') > (3 if lang == 'fr' else 2) and '/cocktails/' in path else 'website'
    robots = '<meta name="robots" content="noindex">\n' if noindex else ''
    return f'''<!doctype html>
<html lang="{lang}"{style}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{robots}<meta name="theme-color" content="{theme}">
{links}<meta property="og:site_name" content="Dernier Verre">
<meta property="og:type" content="{kind}">
<meta property="og:url" content="{SITE}{path}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(title)}">
<meta property="og:locale" content="{u['locale']}">
<meta property="og:locale:alternate" content="{UI[other]['locale']}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preload" href="{up}assets/fonts/archivo-latin.woff2" as="font" type="font/woff2" crossorigin>
<style>{fonts(up)}{CSS}</style>
{ld}</head>
<body>
<script>document.documentElement.classList.add('js')</script>
<a class="skip" href="#top">{u['skip']}</a>
<header class="site surface">
  <div class="col pad">
    <a href="{home or './'}" class="logo poster" aria-label="Dernier Verre — {e(u['home'])}"><i aria-hidden="true"></i>Dernier Verre</a>
    <nav class="main" aria-label="Sections">
      <a href="{home}#how">{u['nav_how']}</a>
      <a href="{home}#bar">{u['nav_bar']}</a>
      <a href="{home}#features">{u['nav_features']}</a>
      <a href="{home}cocktails/">{u['nav_recipes']}</a>
      <a href="{home}#faq">{u['nav_faq']}</a>
    </nav>
    {switch}
    <a class="pill" href="{home}#download">{u['get_app']}</a>
  </div>
</header>
'''

def foot(lang, up, scripts=('site.js',)):
    u, home = UI[lang], up + PREFIX[lang]
    js = ''.join(f'<script src="{up}assets/{s}" defer></script>\n' for s in scripts)
    return f'''<footer class="surface">
  <div class="col pad">
    <div>
      <a href="{home or './'}" class="logo poster">Dernier Verre</a>
      <p class="body muted" style="margin-top:10px">{u['tagline']}</p>
    </div>
    <nav aria-label="Footer">
      <a href="{home}#how">{u['nav_how']}</a>
      <a href="{home}#bar">{u['nav_bar']}</a>
      <a href="{home}#features">{u['nav_features']}</a>
      <a href="{home}cocktails/">{u['all_recipes']}</a>
      <a href="{home}#faq">{u['nav_faq']}</a>
    </nav>
    <div class="legal">
      <span class="legal-left"><span>© <span id="year">{date.today().year}</span> Dernier Verre</span> <span class="credit">{u['credit'].replace('{heart}', HEART)}</span></span>
      <span>{u['drink_resp']}</span>
    </div>
  </div>
</footer>
{js}</body>
</html>
'''

def tile(c, lang, home, heading='h3'):
    ings = ' · '.join(re.sub(r'\s*\(.*\)$', '', DATA[lang]['ingredients'][m['id']]) for m in c['ingredients'] if not m.get('optional'))
    return (f'<a class="tile" href="{home}cocktails/{c["id"]}/" data-base="{c["base"]}" style="--bg:{c["color"]};--ink:{c["ink"]}">'
            f'<p class="kicker">N° {c["n"]:02d} · {e(DATA[lang]["labels"]["base"][c["base"]])}</p>'
            f'<div><{heading} class="poster">{e(c["name"])}</{heading}><p class="ing">{e(ings)}</p></div></a>')

def crumbs(items):
    return {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i, 'name': n, 'item': SITE + p} for i, (n, p) in enumerate(items, 1)]}

def write(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

BY_BASE = {lang: {} for lang in LANGS}
for lang in LANGS:
    for c in C[lang]: BY_BASE[lang].setdefault(c['base'], []).append(c)
N = len(recipes)
sitemap = []  # (path_en, path_fr)

for lang in LANGS:
    u, d, P = UI[lang], DATA[lang], PREFIX[lang]
    L = d['labels']

    # ---------- assets/data.<lang>.js ----------
    data = {
        'cocktails': [{'id': c['id'], 'name': c['name'], 'tagline': c['tagline'], 'base': c['base'], 'color': c['color'],
                       'ing': [[m['id'], m.get('ml'), bool(m.get('optional'))] for m in c['ingredients']]} for c in C[lang]],
        'ingredients': d['ingredients'], 'base': L['base'], 'ui': u['js'],
    }
    write(f'assets/data.{lang}.js', '/* Generated by tools/build.py — do not edit. */\nwindow.DV = '
          + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')

    # ---------- home ----------
    path, alt = f'/{P}', {'en': '/', 'fr': '/fr/'}
    up = up_for(path)
    faq = '\n'.join(f'    <details><summary><h3 class="poster">{q}</h3><span class="plus" aria-hidden="true">+</span></summary><p class="body">{a}</p></details>'
                    for q, a in u['faq'])
    library = '\n'.join(tile(c, lang, '') for c in C[lang]) + (
        f'\n<div class="tile end"><p class="poster">{u["thats_all"]}</p><p class="body">{u["cant_choose"]}</p>'
        f'<button type="button" class="pill" id="surprise">{u["surprise_me"]}</button></div>')
    values = {**{k: v for k, v in u.items() if isinstance(v, str)},
              'lib_count': u['lib_count'].format(n=N), 'lib_h2': u['lib_h2'].format(n=N),
              'store_button': store_button(u['cta_download']), 'library': library, 'faq': faq,
              'swatches': ''.join(f'<i style="background:{c["color"]}"></i>' for c in C[lang][::4])}
    body = re.sub(r'\{\{(\w+)\}\}', lambda m: values[m[1]], HOME)
    app = {'@type': 'MobileApplication', '@id': f'{SITE}/#app', 'name': 'Dernier Verre', 'operatingSystem': 'iOS',
           'applicationCategory': 'LifestyleApplication', 'description': u['home_desc'], 'image': f'{SITE}/assets/icons/icon-1024.png',
           'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'CAD'}, 'author': {'@id': ORG['@id']}, 'publisher': {'@id': ORG['@id']}}
    graph = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'WebSite', '@id': f'{SITE}/#website', 'url': SITE + '/', 'name': 'Dernier Verre', 'inLanguage': lang, 'publisher': {'@id': ORG['@id']}},
        ORG, app,
        {'@type': 'FAQPage', 'url': SITE + path, 'inLanguage': lang, 'mainEntity': [
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in u['faq']]},
    ]}
    write(f'{P}index.html', head(lang, u['home_title'], u['home_desc'], path, alt, [graph], image=f'{SITE}/assets/og/{lang}/home.jpg')
          + body + foot(lang, up, (f'data.{lang}.js', 'site.js', 'home.js')))
    if lang == 'en': sitemap.append(('/', '/fr/'))

    # ---------- one page per cocktail ----------
    for i, c in enumerate(C[lang]):
        path = f'/{P}cocktails/{c["id"]}/'
        alt = {'en': f'/cocktails/{c["id"]}/', 'fr': f'/fr/cocktails/{c["id"]}/'}
        up = up_for(path)
        home = up + P
        base, glass = L['base'][c['base']], L['glass'][c['glass']]
        prev, nxt = C[lang][i - 1], C[lang][(i + 1) % N]
        s1, s2 = summary(c, lang)
        title = (u['recipe_title_free'] if c['base'] == 'sansAlcool' else u['recipe_title']).format(name=c['name'])
        img_w, img_s = f'{SITE}/assets/og/{lang}/{c["id"]}.jpg', f'{SITE}/assets/og/{lang}/{c["id"]}-1x1.jpg'
        recipe_ld = {
            '@context': 'https://schema.org', '@type': 'Recipe', 'name': c['name'], 'description': f'{s1} {c["description"]}',
            'image': [img_s, img_w], 'url': SITE + path, 'inLanguage': lang,
            'author': {'@type': 'Organization', 'name': 'Dernier Verre', 'url': SITE + '/'},
            'publisher': ORG,
            'recipeCategory': 'Cocktail' if c['base'] != 'sansAlcool' else ('Mocktail' if lang == 'en' else 'Cocktail sans alcool'),
            'keywords': ', '.join([base] + [L['flavors'][f] for f in c['flavors']] + [L['occasions'][o][1] for o in c['occasions']]),
            'recipeYield': '1 drink' if lang == 'en' else '1 verre',
            'recipeIngredient': [f'{qty(m, lang)} {d["ingredients"][m["id"]]}' if ('ml' in m or 'count' in m) else f'{d["ingredients"][m["id"]]} — {qty(m, lang)}'
                                 for m in c['ingredients']],
            'recipeInstructions': [{'@type': 'HowToStep', 'position': j, 'text': s} for j, s in enumerate(c['steps'], 1)],
        }
        bc = crumbs([(u['home'], f'/{P}'), (u['nav_recipes'], f'/{P}cocktails/'), (c['name'], path)])

        facts = ''.join(f'<div class="fact"><p class="kicker">{k}</p><p class="poster">{e(v)}</p></div>' for k, v in [
            (u['strength'], L['strength'][c['strength']]), (u['difficulty'], L['difficulty'][c['difficulty']]), (u['method'], L['method'][c['method']])])
        tags = ''.join(f'<span class="tagpill">{o[0]} {e(o[1])}</span>' for o in (L['occasions'][x] for x in c['occasions']))
        tags += ''.join(f'<span class="tagpill">{e(L["flavors"][x])}</span>' for x in c['flavors'])
        ings = ''.join(
            f'<li class="ing-row"><span><span class="ing-name">{e(d["ingredients"][m["id"]])}</span>'
            + (f'<span class="opt">{u["optional"]}</span>' if m.get('optional') else '')
            + f'</span><span class="poster q"{qty_attrs(m, lang)}>{e(qty(m, lang))}</span></li>' for m in c['ingredients'])
        steps = ''.join(f'<li><span class="poster sn" aria-hidden="true">{j:02d}</span><span>{e(s)}</span></li>' for j, s in enumerate(c['steps'], 1))
        garnish = f'<p class="garnish"><b>{u["garnish"]}</b> {e(c["garnish"])}</p>' if c['garnish'] else ''
        same = [x for x in BY_BASE[lang][c['base']] if x is not c]
        if len(same) < 4:
            same += [x for x in C[lang][i + 1:] + C[lang][:i] if x not in same and x is not c][:4 - len(same)]
        more_title = u['more_with'].format(base=base.lower() if lang == 'en' else base) if len(BY_BASE[lang][c['base']]) > 1 else u['also_like']
        gw = u['glass']

        page = head(lang, title, meta_desc(c, lang), path, alt, [recipe_ld, bc], c['color'], img_w) + f'''
<main class="recipe" id="top">
  <nav class="col pad r-nav" aria-label="Breadcrumb">
    <a class="chip" href="{home}cocktails/">{u["back"]}</a>
    <span class="kicker">N° {c["n"]:02d} / {N}</span>
  </nav>

  <article>
  <div class="col pad">
    <header class="r-poster">
      <p class="kicker">{e(base)} · {e(glass)}</p>
      <h1 class="poster r-title">{e(c["name"])}</h1>
      <p class="lead">{e(c["tagline"])}</p>
      <div class="facts-row">{facts}</div>
      <div class="tags">{tags}</div>
    </header>
    <p class="r-answer">{e(s1)} {e(s2)}</p>
    <p class="r-desc">{e(c["description"])}</p>
  </div>

  <div class="col pad r-grid">
    <section class="r-ing" aria-labelledby="ing-h">
      <div class="r-ing-head">
        <h2 class="poster" id="ing-h">{u["ingredients"]}</h2>
        <div class="seg" role="group" aria-label="{u["units"]}">
          <button type="button" data-unit="ml" aria-pressed="true">ml</button><button type="button" data-unit="oz" aria-pressed="false">oz</button>
        </div>
      </div>
      <div class="servings">
        <span class="poster" id="servings" aria-live="polite" data-one="{gw[0]}" data-many="{gw[1]}">1 {gw[0]}</span>
        <button type="button" class="circle" data-step="-1" aria-label="{u["fewer"]}">−</button>
        <button type="button" class="circle" data-step="1" aria-label="{u["more_glasses"]}">+</button>
      </div>
      <ul class="ing-list">{ings}</ul>
      {garnish}
    </section>

    <section class="r-steps" aria-labelledby="steps-h">
      <h2 class="poster" id="steps-h">{u["preparation"]}</h2>
      <ol class="step-list">{steps}</ol>
    </section>
  </div>
  </article>

  <section class="col pad" aria-labelledby="app-h">
    <div class="r-app">
      <div>
        <h2 class="poster" id="app-h">{u["app_h2"]}</h2>
        <p class="body">{u["app_body"]}</p>
      </div>
      {store_button(u["download_short"])}
    </div>
  </section>

  <section class="col r-more" aria-labelledby="more-h">
    <div class="pad r-more-head"><h2 class="kicker" id="more-h">{e(more_title)}</h2><a class="kicker" href="{home}cocktails/">{u["all_n"].format(n=N)}</a></div>
    <div class="lib">{"".join(tile(x, lang, home) for x in same[:6])}</div>
  </section>

  <nav class="col pad r-pn" aria-label="{u["prev"]} / {u["next"]}">
    <a href="{home}cocktails/{prev["id"]}/" rel="prev"><span class="kicker">{u["prev"]}</span><span class="poster">{e(prev["name"])}</span></a>
    <a href="{home}cocktails/{nxt["id"]}/" rel="next" class="next"><span class="kicker">{u["next"]}</span><span class="poster">{e(nxt["name"])}</span></a>
  </nav>
</main>
''' + foot(lang, up, ('site.js', 'recipe.js'))
        write(f'{P}cocktails/{c["id"]}/index.html', page)
        if lang == 'en': sitemap.append((alt['en'], alt['fr']))

    # ---------- all recipes, grouped by spirit ----------
    path, alt = f'/{P}cocktails/', {'en': '/cocktails/', 'fr': '/fr/cocktails/'}
    up = up_for(path)
    home = up + P
    order = [k for k in L['base'] if k in BY_BASE[lang]]
    groups = ''.join(f'''
  <section class="col r-group" id="{k}" aria-labelledby="g-{k}">
    <div class="pad r-more-head"><h2 class="kicker" id="g-{k}">{e(L["base"][k])}</h2><span class="kicker">{len(BY_BASE[lang][k])}</span></div>
    <div class="lib">{"".join(tile(c, lang, home) for c in BY_BASE[lang][k])}</div>
  </section>''' for k in order)
    jump = ''.join(f'<a class="chip" href="#{k}">{e(L["base"][k])}</a>' for k in order)
    item_list = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': u['list_title'].format(n=N), 'url': SITE + path,
                 'inLanguage': lang, 'mainEntity': {'@type': 'ItemList', 'numberOfItems': N, 'itemListElement': [
                     {'@type': 'ListItem', 'position': c['n'], 'url': f'{SITE}/{P}cocktails/{c["id"]}/', 'name': c['name']} for c in C[lang]]}}
    bc = crumbs([(u['home'], f'/{P}'), (u['nav_recipes'], path)])
    write(f'{P}cocktails/index.html', head(lang, u['list_title'].format(n=N), u['list_desc'].format(n=N), path, alt, [item_list, bc],
          image=f'{SITE}/assets/og/{lang}/cocktails.jpg') + f'''
<main id="top">
  <section class="col pad r-hero">
    <p class="kicker">{u["list_kicker"].format(n=N)}</p>
    <h1 class="poster r-title list-title">{u["list_h1"]}</h1>
    <p class="lead">{u["list_lead"]}</p>
    <nav class="lib-filters jump" aria-label="{u["jump_label"]}">{jump}</nav>
  </section>
  {groups}
</main>
''' + foot(lang, up, ('site.js', 'recipe.js')))
    if lang == 'en': sitemap.insert(1, ('/cocktails/', '/fr/cocktails/'))

# ---------- 404 (one page for both languages; served for any missing URL, so root-absolute links) ----------
en, fr = UI['en'], UI['fr']
write('404.html', head('en', en['nf_title'], en['nf_desc'], '/404.html', {'en': '/', 'fr': '/fr/'}, noindex=True, base='/') + f'''
<main class="col pad r-hero" id="top" style="min-height:60vh">
  <p class="kicker">404</p>
  <h1 class="poster r-title">{en["nf_h1"]}</h1>
  <p class="lead">{en["nf_lead"]}</p>
  <p class="lead" lang="fr">{fr["nf_lead"]}</p>
  <p><a class="pill" href="/">{en["nf_back"]}</a> <a class="pill ghost" href="/fr/" lang="fr">{fr["nf_back"]}</a></p>
</main>
''' + foot('en', '/'))

# ---------- sitemap with language alternates ----------
def url(en_p, fr_p, loc):
    alts = ''.join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{SITE}{p}"/>' for l, p in (('en', en_p), ('fr', fr_p), ('x-default', en_p)))
    return f'  <url><loc>{SITE}{loc}</loc><lastmod>{TODAY}</lastmod>{alts}</url>\n'
write('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
      + ''.join(url(a, b, a) + url(a, b, b) for a, b in sitemap) + '</urlset>\n')

# ---------- llms.txt: a plain summary for answer engines ----------
lines = ['# Dernier Verre', '', f'> {en["home_desc"]}', '',
         'Dernier Verre is a free iPhone app by Wibeset (Quebec, Canada), coming soon to the App Store. It needs no account, works offline, keeps your bar on your phone, '
         f'and contains {N} cocktail recipes with exact measures in ml or oz, scalable from 1 to 12 glasses. '
         'Tick the ingredients you own and the app shows what you can make.', '',
         '## Pages', f'- [Home]({SITE}/): what the app does, FAQ',
         f'- [All {N} cocktail recipes]({SITE}/cocktails/)', f'- [Version française]({SITE}/fr/)', '',
         '## FAQ'] + [f'- **{q}** {a}' for q, a in en['faq']] + ['', '## Recipes'] + [
         f'- [{c["name"]}]({SITE}/cocktails/{c["id"]}/): {" ".join(summary(c, "en"))}' for c in C['en']] + ['']
write('llms.txt', '\n'.join(lines))

# ---------- misc ----------
write('site.webmanifest', json.dumps({
    'name': 'Dernier Verre', 'short_name': 'Dernier Verre', 'start_url': '/', 'scope': '/', 'display': 'standalone',
    'theme_color': '#F4F2EC', 'background_color': '#F4F2EC',
    'icons': [{'src': '/android-chrome-192x192.png', 'sizes': '192x192', 'type': 'image/png'},
              {'src': '/android-chrome-512x512.png', 'sizes': '512x512', 'type': 'image/png'},
              {'src': '/assets/icons/icon-maskable-192.png', 'sizes': '192x192', 'type': 'image/png', 'purpose': 'maskable'},
              {'src': '/assets/icons/icon-maskable-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'}]}, indent=1) + '\n')
write('robots.txt', f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n')
write('CNAME', 'dernierverre.app\n')
write('.nojekyll', '')
print(f'Built {N} recipes × {len(LANGS)} languages, home, recipe lists, 404, sitemap ({len(sitemap) * 2} URLs), llms.txt.')
