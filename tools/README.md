# Building dernierverre.app

Static HTML in English (`/`) and French (`/fr/`), hosted on GitHub Pages at https://dernierverre.app
(see `CNAME`). Every HTML page is **generated** — edit the sources, then rebuild from the repo root.

## Sources

| Path | What it is |
| --- | --- |
| `src/home.html` | Home page body with `{{key}}` placeholders |
| `data/ui.json` | Interface text, `en` and `fr` (home copy, FAQ, labels, recipe-page strings) |
| `data/recipes.json` | Recipes extracted from the app: French names, taglines, steps, garnishes, quantities, colours |
| `data/en.json` | English recipe copy (names, taglines, descriptions, steps, garnishes) and labels |
| `data/fr.json` | French descriptions and labels |
| `assets/site.css` | All styles. Colours and type follow the app's `Theme` (Components.swift) |
| `assets/home.js`, `recipe.js`, `site.js` | Hero preview and "My bar" demo; ml/oz and glasses; FAQ and reveal |
| favicons at the root, `assets/icons/` | From the app's icon set (`~/Desktop/dernierverre-icons`) |

## Build

```sh
python3 tools/build.py      # all pages, both languages, data.<lang>.js, sitemap, llms.txt, 404
python3 tools/images.py     # link-preview and recipe images in assets/og/<lang>/ (macOS + Chrome; slow)
python3 tools/images.py home  # only the home and recipe-list images
```

`build.py` stops if a cocktail is missing English copy or a French description, or if its step
count differs from the app's. Commit everything it writes: GitHub Pages serves the repo as is.

## Updating recipes from the app

```sh
python3 tools/extract.py ../dernierverre-ios/Cocktails/Model/CocktailLibrary.swift
# add/adjust copy for new or changed cocktails in data/en.json and data/fr.json
python3 tools/build.py && python3 tools/images.py <new-ids>
```

## SEO / AEO notes

- Each page has a canonical URL, `hreflang` links to its other language (+ `x-default` → English),
  Open Graph and Twitter tags with a generated image.
- Structured data: `WebSite`, `Organization`, `MobileApplication` and `FAQPage` on the home pages;
  `CollectionPage` + `ItemList` on the recipe lists; `Recipe` (with images) + `BreadcrumbList` on each cocktail.
- Each recipe opens with a one-sentence answer ("A Negroni is made with…"), also used as the meta description.
- `llms.txt` summarizes the app, the FAQ and every recipe for answer engines.
- `sitemap.xml` lists both languages with alternates.

## Before launch

- Set `APP_STORE` in `tools/build.py` to the App Store URL, then rebuild: the "coming soon" pills become download links. When the app has an
  App Store ID, consider adding `<meta name="apple-itunes-app" content="app-id=…">` in `head()`.

## Preview locally

```sh
python3 -m http.server 8000   # then open http://localhost:8000 and http://localhost:8000/fr/
```
