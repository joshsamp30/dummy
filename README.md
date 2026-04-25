# Eric Kjelshus Energy — Website

Premium static homepage for Eric Kjelshus Energy Heating &amp; Cooling
(Greenwood, MO). Built from scratch in plain HTML / CSS / JS — no build
step, no framework — designed for fast load, strong on-page SEO and
easy editing.

## Files

- `index.html` — page structure, copy and JSON-LD structured data
- `styles.css` — all styling
- `script.js` — mobile nav, scrollspy, form placeholder, year stamp
- `robots.txt` — crawler rules
- `sitemap.xml` — sitemap for search engines

## Run locally

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## SEO already wired up

- Semantic HTML5 (`header`, `nav`, `main`, `section`, `article`, `footer`)
- Title + meta description tuned for "HVAC Kansas City / Greenwood MO"
- Open Graph + Twitter Card tags
- Canonical URL + robots meta
- JSON-LD `HVACBusiness` (NAP, hours, geo, rating, services, area served)
- JSON-LD `FAQPage` for FAQ rich result eligibility
- Inline SVG favicon (no broken icon)
- Skip-to-content link, ARIA labels, alt-equivalent SVG handling
- `tel:` links throughout for one-tap mobile calls
- `robots.txt` + `sitemap.xml`

## Customising

- **Brand colours:** edit `:root` in `styles.css` (`--blue`, `--red`, `--navy`, `--gold`).
- **Phone / address / hours:** search `816-537-5100`, `25001 E Outer Belt Rd`, and the `openingHoursSpecification` block in `index.html`.
- **Hero photo:** `.hero-photo` currently uses a CSS-rendered HVAC illustration. Swap in a real photo by replacing the `background` and `background-image` rules in `styles.css` (e.g. `background-image: url('images/technician.jpg')`).
- **About photo:** same pattern on `.about-photo`.
- **Form:** wire `<form class="contact-form">` to your backend, Formspree or Netlify Forms. Current handler in `script.js` is a placeholder.
- **Sitemap / canonical / OG image:** replace `https://ericsenergy.com/` with the real production domain everywhere it appears.

## Recommended next steps

1. Drop in real photography (hero, technician, vans, before/afters) at the marked locations.
2. Add Google Tag Manager + GA4 in `<head>` for analytics.
3. Submit `sitemap.xml` to Google Search Console and Bing Webmaster Tools.
4. Verify the `HVACBusiness` schema with Google's Rich Results Test.
5. Build out individual service pages (`/services/geothermal`, `/services/heating`, etc.) and city landing pages for local SEO (e.g. `/hvac-blue-springs-mo`).
