(() => {
  // Mobile nav toggle
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.getElementById("primary-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const open = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!open));
      nav.classList.toggle("is-open", !open);
      toggle.setAttribute("aria-label", open ? "Open menu" : "Close menu");
    });

    nav.querySelectorAll("a").forEach((a) =>
      a.addEventListener("click", () => {
        if (window.matchMedia("(max-width: 1024px)").matches) {
          toggle.setAttribute("aria-expanded", "false");
          nav.classList.remove("is-open");
        }
      })
    );
  }

  // Active nav highlighting on scroll
  const sections = ["home", "about", "services", "resources", "blog", "gallery", "contact"]
    .map((id) => document.getElementById(id))
    .filter(Boolean);
  const navLinks = nav ? Array.from(nav.querySelectorAll(".nav-list a")) : [];
  if (sections.length && navLinks.length && "IntersectionObserver" in window) {
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            const id = e.target.id;
            navLinks.forEach((l) =>
              l.classList.toggle("active", l.getAttribute("href") === `#${id}`)
            );
          }
        });
      },
      { rootMargin: "-45% 0px -50% 0px", threshold: 0 }
    );
    sections.forEach((s) => obs.observe(s));
  }

  // Contact form — placeholder handler (replace with real backend / Formspree / Netlify)
  const form = document.querySelector(".contact-form");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const btn = form.querySelector("button[type=submit]");
      if (!btn) return;
      const original = btn.textContent;
      btn.textContent = "Sending…";
      btn.disabled = true;
      setTimeout(() => {
        btn.textContent = "Thanks — we'll be in touch shortly";
        form.reset();
        setTimeout(() => {
          btn.textContent = original;
          btn.disabled = false;
        }, 3500);
      }, 700);
    });
  }

  // Auto-update copyright year
  const yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = new Date().getFullYear();
})();
