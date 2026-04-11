# The Sign Group — Template

A static, single-page website template for a bespoke signage business,
inspired by the structure of typical sign company sites (hero, services,
projects, about, process, contact).

## Contents

- `index.html` — page structure and copy
- `styles.css` — all styling (no frameworks, no build step)

## Run it

Just open `index.html` in a browser, or serve the folder with any static
server, for example:

```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Customise

- **Brand colour:** change `--brand` in `styles.css` (`:root` block).
- **Logo text:** edit the `.logo` markup in `index.html`.
- **Copy:** all text is plain HTML — edit directly in `index.html`.
- **Project tiles:** replace the CSS gradients on `.tile-1` … `.tile-6`
  with real photos via `background-image: url(...)`.
- **Form:** the contact form is a placeholder. Wire it up to your backend,
  Formspree, Netlify Forms, etc.

## Notes

This is an original template, not a copy of any specific existing website.
Swap in your own brand, copy and imagery before using it in production.
