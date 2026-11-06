# dernierverre.app

Marketing site for **Dernier Verre**, the iPhone cocktail app. Static HTML, hosted on
GitHub Pages at https://dernierverre.app (see `CNAME`).

## Layout

| Path | What it is |
| --- | --- |
| `index.html` | One-pager. Hand-written, except the regions between `<!-- build:… -->` markers |
| `cocktails/<id>/` | One generated page per cocktail (recipe, measures, steps, schema.org `Recipe`) |
| `cocktails/index.html` | Every recipe, grouped by spirit (generated) |
| `assets/site.css` | All styles. Colours and type follow the app's `Theme` (Components.swift) |
| `assets/home.js` | Hero phone preview, "My bar" demo, library filters |
| `assets/recipe.js` | ml/oz switch and 1–12 glasses on recipe pages |
| `assets/data.js` | Generated recipe data for `home.js` |
| `data/recipes.json` | Recipes extracted from the app (French source text, quantities, colours) |
| `data/en.json` | English copy: names, taglines, descriptions, steps, garnishes, labels |

## Updating recipes

The app is the source of truth. After changing `CocktailLibrary.swift`:

```sh
python3 tools/extract.py ../dernierverre-ios/Cocktails/Model/CocktailLibrary.swift
# add/adjust the English copy for any new or changed cocktail in data/en.json
python3 tools/build.py
```

`build.py` stops with an error if a cocktail has no English copy or its step count
differs from the app's. It also rewrites `sitemap.xml`, `robots.txt`, `404.html`,
`CNAME` and `.nojekyll`. Commit the generated files: GitHub Pages serves the repo as is.

## Before launch

- Set `APP_STORE` in `tools/build.py` and the `href` of the `data-appstore` links in
  `index.html` to the App Store URL, then rebuild.

## Preview locally

```sh
python3 -m http.server 8000   # then open http://localhost:8000
```
