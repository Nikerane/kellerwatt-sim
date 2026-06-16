# Design: KellerWatt Website on kellerwatt.de (Vercel)

**Date:** 2026-06-16
**Status:** approved, pending implementation

## Goal

Move the KellerWatt landing page off `nikerane.github.io/kellerwatt/` and onto its own domain `kellerwatt.de`, hosted on Vercel from a new standalone GitHub repo. Optionally add the simulator at `/sim/` later via a git submodule.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Hosting | Vercel | Already used by the project (`vercel.json` exists), first-class static hosting, free SSL, GitHub auto-deploy |
| Domain | `kellerwatt.de` (already purchased at Squarespace) | German brand, German audience, .de signals local trust |
| Repo structure | New repo `kellerwatt-website`, Separate from `kellerwatt-sim` | Landing page lifecycle is independent of the simulator; simulator may not be needed long-term |
| Simulator integration | Git submodule (deferred) | Optional, cleanly pins a version, removable without touching landing page |
| Landing page | Extracted from `nikerane.github.io/kellerwatt/index.html` | Already written, branded, and complete — just relocate it |
| Video | External host (Vercel Blob) | `kw-film.mp4` is a large binary; Git is not the right place for it |
| Build | None — pure static HTML/CSS/JS | The landing page is a single self-contained HTML file with inline styles and vanilla JS |

## Architecture

```
  kellerwatt-website/                  ← NEW repo, owned by Nikerane
  ├── index.html                       ← extracted landing page
  ├── assets/
  │   ├── colors_and_type.css
  │   ├── hero.png
  │   └── (any other images/fonts)
  ├── tweaks-panel.jsx                 ← React/Babel tweaks editor
  ├── vercel.json                      ← { "outputDirectory": "." }
  └── README.md

  kellerwatt-sim/                      ← existing repo, UNCHANGED
  └── web/                             ← simulator app (Vite + React + TS)
      └── (later: consumed as a git submodule at kellerwatt-website/sim/)
```

## Step-by-step implementation

### 1. Create the new repo

- Create `github.com/Nikerane/kellerwatt-website` (public)
- Clone locally to `~/repos/kellerwatt-website`

### 2. Extract the landing page

Source: `/tmp/nikerane.github.io/kellerwatt/index.html`
Assets needed:
- `assets/hero.png` — hero background image
- `assets/colors_and_type.css` — design token CSS variables
- `tweaks-panel.jsx` — React/Babel tweaks panel component
- (film video handled separately)

Changes to make in `index.html`:
- Replace all `nikerane.github.io` absolute URLs with `kellerwatt.de` equivalents
- Nav "Simulator" link stays pointing to `nikerane.github.io/kellerwatt-sim/` for now
- Point video `src` at the Vercel Blob URL (or comment it out temporarily)
- Update `og:url` and other meta tags to `kellerwatt.de`

### 3. Configure Vercel

- Create a new project in Vercel dashboard
- Connect to `Nikerane/kellerwatt-website` GitHub repo
- Framework preset: "Other" (or "No Framework" — it's static HTML)
- Output directory: `.` (root)
- No build command needed

### 4. Connect kellerwatt.de domain

In Squarespace DNS settings (`Settings` → `Domains` → `kellerwatt.de` → `DNS Settings`):
- Remove any default Squarespace DNS records
- Add A record: `@` → `76.76.21.21`
- Add CNAME record: `www` → `cname.vercel-dns.com`

In Vercel project settings (`Settings` → `Domains`):
- Add `kellerwatt.de`
- Vercel offers to add `www.kellerwatt.de` → accept (auto-redirects to apex)
- Vercel auto-verifies DNS and provisions SSL certificate

### 5. Handle the video

- Upload `kw-film.mp4` to Vercel Blob (via CLI: `npx vercel-blob upload kw-film.mp4` or through the Vercel dashboard)
- Replace the `<source src="kw-film.mp4">` with the Vercel Blob URL
- Update `poster` attribute similarly if `film-poster.jpg` is also large

### 6. Remove KellerWatt from nikerane.github.io

- Delete `/kellerwatt/` directory from `nikerane.github.io`
- Update `nikerane.github.io/index.html` nav: change `./kellerwatt/index.html` → `https://kellerwatt.de`
- Push both changes

### 7. Verification checklist

- [ ] `kellerwatt.de` loads the landing page with HTTPS
- [ ] `www.kellerwatt.de` redirects to `kellerwatt.de`
- [ ] Hero image loads
- [ ] Tweaks panel works (hero composition, palette, headline voice changes)
- [ ] Nav links work (smooth scrolling to sections)
- [ ] Email form works
- [ ] Film section renders (video loads from Vercel Blob if available)
- [ ] Old `nikerane.github.io/kellerwatt/` redirects or 404s gracefully
- [ ] `nikerane.github.io` nav now links to `kellerwatt.de`

## Future: adding the simulator

When the simulator is ready to join the domain:

```
kellerwatt-website/
├── index.html
├── sim/                     ← git submodule add https://github.com/Nikerane/kellerwatt-sim.git sim
│   └── web/dist/            ← tracked from kellerwatt-sim's built output branch
├── vercel.json
└── ...
```

**`vercel.json` for subpath routing:**
```json
{
  "rewrites": [
    { "source": "/sim/:path*", "destination": "/sim/:path*" }
  ]
}
```

The simulator's `vite.config.ts` already has `base: "./"` — this means relative asset paths work at any subpath, including `/sim/`. No config changes needed on the simulator side.

**Workflow:**
1. `kellerwatt-sim` CI builds to `web/dist/` and commits to a `dist` branch (or we use a build hook)
2. `kellerwatt-website` pins the submodule to a known-good commit
3. Vercel re-deploys on push — the `/sim/` subpath serves the built simulator

## Risks

- **DNS propagation**: Can take up to 48 hours. In practice, ~15-30 minutes. Minimal risk — the old GitHub Pages URL still works during transition.
- **Squarespace DNS UI**: Squarespace sometimes buries the DNS settings. If it's hard to find, the backup plan is to use Vercel's nameservers method instead (switch Squarespace to custom nameservers, manage all DNS inside Vercel).
- **Video hosting cost**: Vercel Blob charges per GB stored and per GB served. At landing-page traffic levels this is negligible, but worth monitoring if traffic spikes.
