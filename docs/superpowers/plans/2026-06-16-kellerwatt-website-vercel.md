# kellerwatt.de Website Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the KellerWatt landing page off `nikerane.github.io/kellerwatt/` onto `kellerwatt.de` via a new `kellerwatt-website` GitHub repo deployed to Vercel.

**Architecture:** Static HTML/CSS/JS landing page extracted from `nikerane.github.io/kellerwatt/` into a new standalone repo. Vercel serves it with zero build step. Domain `kellerwatt.de` (Squarespace) connected via A/CNAME records. Video hosted on Vercel Blob. Simulator submodule deferred to a future plan.

**Tech Stack:** Plain HTML/CSS/JS, React 18 + Babel standalone (CDN, for tweaks panel), Google Fonts CDN, Vercel static hosting.

---

### File Structure

Files to create in the new `kellerwatt-website` repo:

```
kellerwatt-website/
├── index.html                        ← extracted & modified from nikerane.github.io/kellerwatt/
├── assets/
│   ├── colors_and_type.css           ← copied verbatim
│   └── hero.png                      ← copied verbatim (2MB)
├── tweaks-panel.jsx                  ← copied verbatim (26KB React/Babel tweaks editor)
├── film-poster.jpg                   ← copied verbatim (44KB)
├── vercel.json                       ← NEW: { "outputDirectory": "." }
└── README.md                         ← NEW: brief repo overview
```

Files deliberately NOT copied (not served to users):
- `kw-film.mp4` (~6.4MB) — goes to Vercel Blob
- `kw-film.html` (~720KB) — original animation source, kept only for future edits in the old repo
- `tools/render-film.mjs` — film rendering script, not needed in production
- `README.md`, `README.txt` — old package docs

---

### Task 0: Create the new GitHub repo and clone it locally

**Note:** This task requires the GitHub CLI (`gh`) or the GitHub web UI.

- [ ] **Step 1: Create the repo on GitHub**

Run:
```bash
gh repo create Nikerane/kellerwatt-website --public --description "KellerWatt landing page — kellerwatt.de"
```

Expected: new empty repo at `https://github.com/Nikerane/kellerwatt-website`

If `gh` is not authenticated, create it manually at https://github.com/new (name: `kellerwatt-website`, public, no README/license/gitignore).

- [ ] **Step 2: Clone the new repo**

```bash
git clone https://github.com/Nikerane/kellerwatt-website.git ~/repos/kellerwatt-website
cd ~/repos/kellerwatt-website
```

Expected: empty repo cloned to `~/repos/kellerwatt-website`.

---

### Task 1: Copy assets verbatim from the old site

**Files:**
- Create: `assets/colors_and_type.css`
- Create: `assets/hero.png`
- Create: `tweaks-panel.jsx`
- Create: `film-poster.jpg`

- [ ] **Step 1: Create the assets directory and copy files**

```bash
cd ~/repos/kellerwatt-website
mkdir -p assets
cp /tmp/nikerane.github.io/kellerwatt/assets/colors_and_type.css assets/
cp /tmp/nikerane.github.io/kellerwatt/assets/hero.png assets/
cp /tmp/nikerane.github.io/kellerwatt/tweaks-panel.jsx .
cp /tmp/nikerane.github.io/kellerwatt/film-poster.jpg .
```

- [ ] **Step 2: Verify files exist**

```bash
ls -la assets/colors_and_type.css assets/hero.png tweaks-panel.jsx film-poster.jpg
```

Expected: all four files listed with non-zero sizes.

---

### Task 2: Adapt the landing page HTML

**Files:**
- Create: `index.html` (modified copy of `/tmp/nikerane.github.io/kellerwatt/index.html`)

Changes from the source:
1. Replace `nikerane.github.io/kellerwatt-sim` → `nikerane.github.io/kellerwatt-sim` in the Simulator link (keep as-is for now — it still works)
2. Update `og:url` meta tag from `nikerane.github.io` → `kellerwatt.de`
3. Remove inline video source (kw-film.mp4) — we'll add Vercel Blob URL in Task 5
4. Update the nav's `Simulator` link text to clarify it's external (no change needed — it already reads fine)

- [ ] **Step 1: Copy the source HTML**

```bash
cp /tmp/nikerane.github.io/kellerwatt/index.html ~/repos/kellerwatt-website/index.html
```

- [ ] **Step 2: Update og:url meta tag**

Open `index.html` and change line 17:
```html
<!-- Before -->
<meta property="og:url" content="https://nikerane.github.io" />
<!-- After -->
<meta property="og:url" content="https://kellerwatt.de" />
```

- [ ] **Step 3: Comment out the video section for now**

Find the `<video>` tag inside the film section (~line 1039-1045). Wrap it so the section still renders but the video element doesn't error on missing source:

```html
<!-- Before (lines 1038-1046) -->
<div class="film-wrap" id="filmWrap">
  <video class="film-frame" id="kwFilm" controls playsinline preload="metadata"
         poster="film-poster.jpg"
         controlsList="nodownload noplaybackrate noremoteplayback"
         disablePictureInPicture disableRemotePlayback>
    <source src="kw-film.mp4" type="video/mp4">
    Your browser can't play this video.
  </video>
</div>

<!-- After -->
<div class="film-wrap" id="filmWrap">
  <video class="film-frame" id="kwFilm" controls playsinline preload="metadata"
         poster="film-poster.jpg"
         controlsList="nodownload noplaybackrate noremoteplayback"
         disablePictureInPicture disableRemotePlayback>
    <!-- Film coming soon — hosted on Vercel Blob -->
    Your browser can't play this video.
  </video>
</div>
```

The poster image still shows, so the section looks intentional rather than broken.

- [ ] **Step 4: Commit**

```bash
cd ~/repos/kellerwatt-website
git add -A
git commit -m "feat: initial landing page extracted from nikerane.github.io/kellerwatt"
```

---

### Task 3: Add vercel.json and README

**Files:**
- Create: `vercel.json`
- Create: `README.md`

- [ ] **Step 1: Create vercel.json**

```bash
cat > ~/repos/kellerwatt-website/vercel.json << 'EOF'
{
  "outputDirectory": "."
}
EOF
```

- [ ] **Step 2: Create README.md**

```bash
cat > ~/repos/kellerwatt-website/README.md << 'EOF'
# kellerwatt.de

KellerWatt landing page. Static HTML/CSS/JS, deployed to Vercel.

## Structure

- `index.html` — the landing page
- `assets/colors_and_type.css` — brand design tokens
- `assets/hero.png` — hero background
- `tweaks-panel.jsx` — live tweaks panel (React/Babel CDN)
- `film-poster.jpg` — video poster frame

## Deploy

Push to `main`. Vercel auto-deploys.

## Domain

`kellerwatt.de` — registered at Squarespace, DNS pointed to Vercel.
EOF
```

- [ ] **Step 3: Push to GitHub**

```bash
cd ~/repos/kellerwatt-website
git add vercel.json README.md
git commit -m "chore: add vercel config and README"
git push origin main
```

---

### Task 4: Create and configure the Vercel project

**Note:** This task is done in the Vercel web dashboard. Parts can also be done via CLI.

- [ ] **Step 1: Import the GitHub repo into Vercel**

Go to https://vercel.com/new → pick `Nikerane/kellerwatt-website`.

Vercel auto-detection will suggest a framework. Override it:
- **Framework:** "Other" (or "No Framework")
- **Output Directory:** `.` (or leave blank — root is default)
- **Build Command:** leave blank (no build step needed)
- **Install Command:** leave blank (no dependencies)

Click **Deploy**. Vercel assigns a `*.vercel.app` preview URL.

- [ ] **Step 2: Verify the preview deployment**

Open the `*.vercel.app` URL Vercel gives you. Check:
- Page loads without errors
- Hero image renders (`assets/hero.png`)
- Tweaks panel works (React/Babel loads from CDN, you can switch palette/voice/composition)
- Nav links work (smooth scroll to sections)
- Film section shows poster image

If anything is broken, fix it in the repo and push — Vercel auto-redeploys.

---

### Task 5: Connect kellerwatt.de domain

**Note:** This requires access to both Squarespace DNS settings and the Vercel dashboard. DNS changes can take 15-60 minutes to propagate (occasionally up to 48 hours).

- [ ] **Step 1: Add the domain in Vercel**

In the Vercel dashboard for `kellerwatt-website`:
1. Go to **Settings** → **Domains**
2. Click **Add Domain**
3. Enter `kellerwatt.de`
4. Vercel prompts to also add `www.kellerwatt.de` → click **Add** to accept both

Vercel now shows DNS instructions for `kellerwatt.de`:
- Type: A, Name: `@`, Value: `76.76.21.21`
- For `www`: Type: CNAME, Name: `www`, Value: `cname.vercel-dns.com`

- [ ] **Step 2: Update DNS records in Squarespace**

1. Log into Squarespace
2. Go to **Settings** → **Domains** → click `kellerwatt.de`
3. Find **DNS Settings** (sometimes under "Advanced DNS" or "Manage DNS")
4. **Delete** any existing A records for `@` (these point to Squarespace)
5. **Delete** any existing CNAME record for `www`
6. **Add** a new A record:
   - Host: `@`
   - Type: A
   - Value: `76.76.21.21`
   - TTL: default (or 3600)
7. **Add** a new CNAME record:
   - Host: `www`
   - Type: CNAME
   - Value: `cname.vercel-dns.com`
   - TTL: default (or 3600)
8. Save

> **Troubleshooting:** If Squarespace's DNS UI doesn't let you add A records (some plans restrict this), use the Vercel Nameservers method instead. In Squarespace, switch to custom nameservers and enter `ns1.vercel-dns.com` and `ns2.vercel-dns.com`. Then in Vercel's domain settings, switch the configuration method to "Nameservers". All DNS is then managed inside Vercel.

- [ ] **Step 3: Wait for Vercel to verify the DNS**

Back in Vercel's domain settings, the status will change from "Configuring" → "Valid" once Vercel detects the DNS records are live. This usually takes 5-15 minutes.

Vercel auto-provisions an SSL certificate (Let's Encrypt) once the domain is verified.

- [ ] **Step 4: Verify kellerwatt.de works**

```
curl -I https://kellerwatt.de
```

Expected: HTTP 200 (or 308 redirect), with `server: Vercel` in the response headers.

Also check `www.kellerwatt.de` redirects to `kellerwatt.de`:
```
curl -I https://www.kellerwatt.de
```

Expected: HTTP 308 redirect with `location: https://kellerwatt.de/`.

---

### Task 6: Upload the video to Vercel Blob and wire it up

**Note:** This task requires the Vercel CLI and the Vercel Blob package. The video is ~6.4MB.

- [ ] **Step 1: Install and configure Vercel Blob**

```bash
cd ~/repos/kellerwatt-website
npm init -y
npm install @vercel/blob
```

Create a one-off upload script:

```bash
cat > upload-film.mjs << 'SCRIPT'
import { put } from '@vercel/blob';
import { readFile } from 'node:fs/promises';

const file = await readFile('/tmp/nikerane.github.io/kellerwatt/kw-film.mp4');
const { url } = await put('kw-film.mp4', file, {
  access: 'public',
  contentType: 'video/mp4',
});

console.log('Vercel Blob URL:', url);
SCRIPT
```

- [ ] **Step 2: Link the local project to Vercel**

```bash
cd ~/repos/kellerwatt-website
npx vercel link
```

Follow the prompts:
- Select the team (your personal account)
- Link to existing project "kellerwatt-website"

- [ ] **Step 3: Run the upload**

```bash
node upload-film.mjs
```

Expected output: a URL like `https://<id>.public.blob.vercel-storage.com/kw-film.mp4`

- [ ] **Step 4: Update index.html with the Blob URL**

Open `index.html`. Replace the commented-out `<video>` section:

```html
<!-- Find the film section (currently has an empty <video> tag) -->
<div class="film-wrap" id="filmWrap">
  <video class="film-frame" id="kwFilm" controls playsinline preload="metadata"
         poster="film-poster.jpg"
         controlsList="nodownload noplaybackrate noremoteplayback"
         disablePictureInPicture disableRemotePlayback>
    <source src="<PASTE_Vercel_Blob_URL_HERE>" type="video/mp4">
    Your browser can't play this video.
  </video>
</div>
```

Replace `<PASTE_Vercel_Blob_URL_HERE>` with the actual URL from Step 3.

- [ ] **Step 5: Clean up and commit**

```bash
cd ~/repos/kellerwatt-website
rm upload-film.mjs
git add index.html vercel.json package.json
git commit -m "feat: add film via Vercel Blob"
git push origin main
```

- [ ] **Step 6: Verify the video plays**

Visit `https://kellerwatt.de`, scroll to the film section, click play. The poster image should appear, and the video should play in the browser.

---

### Task 7: Remove KellerWatt from the personal site

**Note:** This modifies your personal website repo at `nikerane.github.io`. The old `/kellerwatt/` URL will stop working — but `kellerwatt.de` is the canonical destination.

- [ ] **Step 1: Navigate to the personal site repo**

```bash
cd /tmp/nikerane.github.io
```

- [ ] **Step 2: Delete the kellerwatt directory**

```bash
git rm -r kellerwatt/
```

- [ ] **Step 3: Update the nav link in index.html**

Open `/tmp/nikerane.github.io/index.html`. On line 31, change:

```html
<!-- Before -->
<li><a href="./kellerwatt/index.html"> KellerWatt</a></li>
<!-- After -->
<li><a href="https://kellerwatt.de"> KellerWatt</a></li>
```

- [ ] **Step 4: Commit and push**

```bash
cd /tmp/nikerane.github.io
git add -A
git commit -m "refactor: move KellerWatt to kellerwatt.de, remove local copy"
git push origin main
```

- [ ] **Step 5: Verify the personal site still works**

Visit `https://nikerane.github.io`. The "KellerWatt" nav link should now point to `https://kellerwatt.de`. The rest of the portfolio should be unchanged.

---

### Task 8: Full verification

Run through the complete checklist on `https://kellerwatt.de`:

- [ ] Page loads with HTTPS (no mixed content warnings)
- [ ] `https://www.kellerwatt.de` redirects to `https://kellerwatt.de`
- [ ] Hero image loads (background on the hero section)
- [ ] Tweaks panel works — switch Hero composition → Cinematic, palette → Dusk, voice → Tagline; all three apply visually
- [ ] Nav links scroll smoothly to sections (#how, #benefits, #join)
- [ ] Email form accepts input and shows success message on submit
- [ ] Vercel Blob video loads (if enabled in Task 6)
- [ ] `https://nikerane.github.io/kellerwatt/` returns 404 (old URL is gone)
- [ ] `https://nikerane.github.io` nav links to `https://kellerwatt.de`

---

### Not in scope (deferred to future plans)

- Git submodule for simulator at `/sim/`
- Fontsource self-hosting (currently Google Fonts CDN — works fine, GDPR concern is low for a static landing page)
- CI/CD beyond Vercel's built-in Git integration
- Analytics or monitoring
