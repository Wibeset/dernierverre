#!/usr/bin/env python3
"""Extract the recipe library from the iOS app into data/recipes.json.

    python3 tools/extract.py ../dernierverre-ios/Cocktails/Model/CocktailLibrary.swift

The app is the source of truth for recipes (French text, quantities, colours).
English copy lives in data/en.json and is written by hand; build.py merges both.
"""
import json, re, sys
from pathlib import Path

src = Path(sys.argv[1]).read_text()
out = []

def split_args(s):
    """Split on top-level commas (ignores commas inside (), [] and strings)."""
    parts, depth, cur, q = [], 0, '', False
    for ch in s:
        if ch == '"' : q = not q
        if not q:
            if ch in '([': depth += 1
            elif ch in ')]': depth -= 1
            elif ch == ',' and depth == 0:
                parts.append(cur.strip()); cur = ''; continue
        cur += ch
    if cur.strip(): parts.append(cur.strip())
    return parts

def body_of(start):
    """Return the text inside the parentheses that open at src[start]."""
    depth, q = 0, False
    for i in range(start, len(src)):
        ch = src[i]
        if ch == '"': q = not q
        if q: continue
        if ch == '(': depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0: return src[start + 1:i]
    raise ValueError('unbalanced')

def strings(s): return re.findall(r'"((?:[^"\\]|\\.)*)"', s)
def enums(s): return re.findall(r'\.(\w+)', s)

def quantity(q):
    if m := re.fullmatch(r'\.ml\(([\d.]+)\)', q): return {'ml': float(m[1])}
    if m := re.fullmatch(r'\.count\(([\d.]+), "([^"]+)"\)', q): return {'count': float(m[1]), 'unit': m[2]}
    if q == '.top': return {'top': True}
    if m := re.fullmatch(r'\.text\("([^"]+)"\)', q): return {'text': m[1]}
    raise ValueError(q)

for m in re.finditer(r'\bCocktail\(\s*id:', src):
    args = {}
    for part in split_args(body_of(m.start() + len('Cocktail'))):
        k, _, v = part.partition(':')
        args[k.strip()] = v.strip()
    ings = []
    # ingredients: parse M(...) calls inside the array text
    text = args['ingredients']
    i = 0
    while (j := text.find('M(', i)) != -1:
        depth, k = 0, j + 1
        for k in range(j + 1, len(text)):
            if text[k] == '(': depth += 1
            elif text[k] == ')':
                depth -= 1
                if depth == 0: break
        parts = split_args(text[j + 2:k])
        ings.append({'id': parts[0].lstrip('.'), **quantity(parts[1]),
                     **({'optional': True} if any('optional: true' in p for p in parts[2:]) else {})})
        i = k + 1
    out.append({
        'id': strings(args['id'])[0],
        'name': strings(args['name'])[0],
        'tagline': strings(args['tagline'])[0],
        'base': args['base'].lstrip('.'),
        'flavors': enums(args['flavors']),
        'occasions': enums(args['occasions']),
        'strength': args['strength'].lstrip('.'),
        'difficulty': args['difficulty'].lstrip('.'),
        'method': args['method'].lstrip('.'),
        'glass': args['glass'].lstrip('.'),
        'color': '#' + args['color'][2:].upper(),
        'ingredients': ings,
        'steps': strings(args['steps']),
        'garnish': (strings(args['garnish']) or [None])[0] if 'garnish' in args else None,
    })

out.sort(key=lambda c: c['name'].lower())
dest = Path(__file__).resolve().parent.parent / 'data' / 'recipes.json'
dest.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
print(f'{len(out)} recipes → {dest}')
