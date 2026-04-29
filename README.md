# Eric Kjelshus Energy — Full Website

Multi-page static site for Eric Kjelshus Energy Heating &amp; Cooling
(Greenwood, MO). Plain HTML / CSS / JS — no build step, no framework —
designed for fast load, strong on-page SEO and easy editing.

## Sitemap (33 pages)

**Top level**
- `index.html` — homepage
- `about.html` · `contact.html` · `faqs.html` · `financing.html`
- `coupons.html` · `reviews.html` · `careers.html` · `blog.html`
- `service-areas.html` · `privacy-policy.html` · `accessibility.html`

**Services (8)**
- `plumbing.html` · `air-conditioning.html` · `heating.html`
- `geothermal.html` · `indoor-air-quality.html` · `electrical.html`
- `commercial.html` · `energy-audits.html`

**Service-area city pages (8)**
- `service-area-greenwood.html` (HQ) · `service-area-lees-summit.html`
- `service-area-blue-springs.html` · `service-area-kansas-city.html`
- `service-area-belton.html` · `service-area-raymore.html`
- `service-area-oak-grove.html` · `service-area-pleasant-hill.html`

**Blog posts (6)**
- `blog-heater-repair-signs.html` · `blog-tankless-water-heater.html`
- `blog-frozen-pipes.html` · `blog-furnace-overheating.html`
- `blog-ductwork-service.html` · `blog-smart-thermostat.html`

**Supporting**
- `styles.css` · `script.js` · `robots.txt` · `sitemap.xml` · `.nojekyll`

## Run locally

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## SEO baked in (every page)

- Semantic HTML5 (`header`, `nav`, `main`, `section`, `article`, `footer`)
- Unique `<title>`, meta description and canonical URL per page
- Open Graph + Twitter Card on key pages
- JSON-LD: `HVACBusiness`, `Service`, `Electrician`, `BlogPosting`,
  `FAQPage`, `AboutPage`, `ContactPage` as appropriate
- Inline-SVG favicon (no extra request, no broken icon)
- Skip-to-content link, ARIA labels, descriptive image alt text
- `tel:` links throughout
- `robots.txt` + comprehensive `sitemap.xml`
- `.nojekyll` for clean GitHub Pages serve

## Image placeholders

To avoid broken images, the site uses CSS-rendered placeholders with
visible labels (e.g. "Plumbing technician on-site"). Swap these with
real photography by replacing the relevant background-image rules
in `styles.css` (search `.img-placeholder`, `.hero-photo`, `.about-photo`).

## Customising

- **Brand colours:** edit `:root` in `styles.css` (`--blue`, `--red`, `--navy`, `--gold`).
- **Phone / address / hours:** search `816-537-5100` and `25001 E Outer Belt Rd`.
- **Form:** wire `<form class="contact-form">` to your backend, Formspree
  or Netlify Forms. Current handler in `script.js` is a placeholder.
- **Production domain:** replace `https://ericsenergy.com/` in canonical
  links, sitemap, OG URLs.

## Recommended next steps

1. Drop in real photography (hero, technician, vans, before/afters).
2. Add Google Tag Manager + GA4 to `<head>` for analytics.
3. Submit `sitemap.xml` to Google Search Console and Bing Webmaster Tools.
4. Verify `HVACBusiness` schema with Google's Rich Results Test.
5. Wire up the contact form to a real backend (Formspree, Netlify Forms,
   or your CRM).
