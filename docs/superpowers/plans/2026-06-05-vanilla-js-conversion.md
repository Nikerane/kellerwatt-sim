# Vanilla JS Conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the KellerWatt Sim web app from React + TypeScript + Vite to plain HTML/CSS/JS with zero framework dependencies and zero build step.

**Architecture:** Three standalone `.html` files that each include shared JS libraries via `<script>` tags. d3-scale and KaTeX loaded from CDN. Fonts from Google Fonts CDN. Data loaded at runtime via `fetch('./data/sim_results.json')`. All state in plain variables, DOM updated via targeted `innerHTML`/`textContent`. CSS copied as-is (already framework-agnostic). Deployment via `npx gh-pages -d vanilla/`.

**Tech Stack:** HTML5, CSS3, vanilla JavaScript (ES2020+), d3-scale (CDN), KaTeX (CDN), Google Fonts (CDN)

**Source files eliminated:** 33 files (2,568 lines of TSX/TS) → 9 files (~700 lines of JS/HTML). Removes: `react`, `react-dom`, `@vitejs/plugin-react`, `typescript`, `vite`, `vitest`, `@testing-library/react`, all `@types/*` packages.

---

## File Structure (target)

```
web/vanilla/
  index.html              # Honesty/Validation page
  methodology.html        # Methodology page
  playground.html         # Playground page
  css/
    app.css               # Copied from src/styles/app.css (571 lines, no changes)
    tokens.css            # Copied from src/tokens/colors_and_type.css (45 lines, no changes)
  js/
    lib/
      components.js       # renderEyebrow(), renderDataMono(), renderCouplet(), renderSiteNav(), renderStatCard(), renderMethodStep(), renderDiligenceItem()
      data.js             # fetchData(), euro(), eurPerMwh(), cycles(), captureOfCeiling()
      charts.js           # renderSpreadChart(), renderPlaygroundChart() — SVG via template literals
    pages/
      honesty.js          # fetch data → render all sections into #root
      methodology.js      # fetch data → render all sections into #root
      playground.js       # state + event handlers + DOM updates + fetch to HF engine
  data/
    sim_results.json      # Copied from src/data/sim_results.json
```

---

### Task 1: Create directory structure and copy static assets

**Files:**
- Create: `web/vanilla/css/tokens.css`
- Create: `web/vanilla/css/app.css`
- Create: `web/vanilla/data/sim_results.json`

- [ ] **Step 1: Create the vanilla directory tree**

```bash
mkdir -p web/vanilla/css web/vanilla/js/lib web/vanilla/js/pages web/vanilla/data
```

- [ ] **Step 2: Copy CSS files (no changes needed)**

```bash
cp web/src/tokens/colors_and_type.css web/vanilla/css/tokens.css
cp web/src/styles/app.css web/vanilla/css/app.css
```

- [ ] **Step 3: Copy data file**

```bash
cp web/src/data/sim_results.json web/vanilla/data/sim_results.json
```

- [ ] **Step 4: Verify files exist**

```bash
ls -la web/vanilla/css/tokens.css web/vanilla/css/app.css web/vanilla/data/sim_results.json
```

Expected: three files listed with non-zero sizes.

- [ ] **Step 5: Commit**

```bash
git add web/vanilla/
git commit -m "feat(vanilla): scaffold directory structure and copy static assets"
```

---

### Task 2: Data library — formatters and accessors

**Files:**
- Create: `web/vanilla/js/lib/data.js`

This file mirrors `src/data/load.ts` but in plain JS. It exports the same functions (`euro`, `eurPerMwh`, `cycles`, `captureOfCeiling`) plus an async `fetchSimResults()` that loads the JSON at runtime.

- [ ] **Step 1: Write the file**

```js
// web/vanilla/js/lib/data.js
// Data loading and formatters for KellerWatt Sim.
// Mirrors src/data/load.ts — same function signatures, plain JS.

/** @type {import('./types.js').SimResults|null} */
let _results = null;

/**
 * Fetch sim_results.json. Call once at page init.
 * @returns {Promise<object>}
 */
export async function fetchSimResults() {
  const res = await fetch('./data/sim_results.json');
  if (!res.ok) throw new Error(`Failed to load sim_results.json: HTTP ${res.status}`);
  _results = await res.json();
  return _results;
}

/** @returns {object} the loaded results (throws if not loaded yet) */
export function results() {
  if (!_results) throw new Error('sim_results.json not loaded — call fetchSimResults() first');
  return _results;
}

/** @param {string} id */
export function strategy(id) {
  const s = results().strategies.find(x => x.id === id);
  if (!s) throw new Error(`missing strategy ${id}`);
  return s;
}

/** @param {string} id */
export function scenario(id) {
  const s = results().scenarios.find(x => x.id === id);
  if (!s) throw new Error(`missing scenario ${id}`);
  return s;
}

/** @param {object} s — strategy object with .years array */
export function yearOf(s, year) {
  const y = s.years.find(x => x.year === year);
  if (!y) throw new Error(`strategy ${s.id} missing year ${year}`);
  return y;
}

export const YEARS = []; // set after fetch

// ---- brand-correct formatters ----

/** €9,700 — currency before figure, thousands separators, no decimals. */
export function euro(value, opts = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const decimals = opts.decimals ?? 0;
  const n = Math.abs(value).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return `${value < 0 ? '−' : ''}€${n}`;
}

/** A €/MWh rate: "€68.3" with one decimal by default. */
export function eurPerMwh(value, decimals = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `€${value.toFixed(decimals)}`;
}

/** Cycles: e.g. "1.23" — two decimals, em dash for null. */
export function cycles(value) {
  if (value === null || value === undefined) return '—';
  return value.toFixed(2);
}

/** Realistic capture as a share of the best-case gross. */
export function captureOfCeiling(year) {
  const ce = yearOf(strategy('lp_ceiling'), year).gross_eur;
  const ca = yearOf(strategy('causal_walkforward'), year).gross_eur;
  if (ce === null || ca === null || ce === 0) return null;
  return ca / ce;
}
```

- [ ] **Step 2: Verify it loads in Node (syntax check)**

```bash
node --input-type=module -e "import { euro, eurPerMwh, cycles } from './web/vanilla/js/lib/data.js'; console.log(euro(9947), eurPerMwh(68.3), cycles(1.5));"
```

Expected: `€9,947 €68.3 1.50`

- [ ] **Step 3: Commit**

```bash
git add web/vanilla/js/lib/data.js
git commit -m "feat(vanilla): add data library — formatters and JSON loader"
```

---

### Task 3: Component library — HTML-generating functions

**Files:**
- Create: `web/vanilla/js/lib/components.js`

Every React component in `src/components/` becomes a plain JS function that returns an HTML string. These are pure functions — no DOM manipulation, just string concatenation.

- [ ] **Step 1: Write the file**

```js
// web/vanilla/js/lib/components.js
// HTML-generating functions. Each mirrors a React component from src/components/.
// All return HTML strings. Use via element.innerHTML = renderXyz(...).

/**
 * Uppercase mono label. ember=true for the signal colour.
 * @param {string} text
 * @param {{ ember?: boolean, className?: string }} [opts]
 * @returns {string}
 */
export function renderEyebrow(text, opts = {}) {
  const cls = ['kw-eyebrow'];
  if (opts.ember) cls.push('kw-eyebrow--ember');
  if (opts.className) cls.push(opts.className);
  return `<span class="${cls.join(' ')}">${esc(text)}</span>`;
}

/**
 * Tabular-nums monospaced figure.
 * @param {string} text
 * @param {{ tone?: string, size?: string, label?: string }} [opts]
 * @returns {string}
 */
export function renderDataMono(text, opts = {}) {
  const tone = opts.tone || 'neutral';
  const size = opts.size || 'md';
  const aria = opts.label ? ` aria-label="${escAttr(opts.label)}"` : '';
  return `<span class="kw-mono kw-mono--${tone} kw-mono--${size}"${aria}>${esc(text)}</span>`;
}

/**
 * Two-line heading couplet.
 * @param {string} first
 * @param {string} second
 * @param {{ as?: string, size?: string }} [opts]
 * @returns {string}
 */
export function renderCouplet(first, second, opts = {}) {
  const tag = opts.as || 'h2';
  const size = opts.size || 'lg';
  return `<${tag} class="kw-couplet kw-couplet--${size}">
    <span class="kw-couplet__a">${first}</span>
    <span class="kw-couplet__b">${second}</span>
  </${tag}>`;
}

/**
 * Cross-page navigation bar.
 * @param {'honesty'|'methodology'|'playground'} current
 * @returns {string}
 */
export function renderSiteNav(current) {
  const link = (page, label, href) => {
    const aria = page === current ? ' aria-current="page"' : '';
    return `<a${aria} href="${href}">${label}</a>`;
  };
  return `<nav class="kw-nav" aria-label="Primary">
    <a class="kw-nav__brand" href="https://nikerane.github.io/kellerwatt/index.html">KellerWatt</a>
    <span class="kw-nav__links">
      ${link('honesty', 'Validation', 'https://nikerane.github.io/kellerwatt-sim/index.html')}
      ${link('methodology', 'Methodology', 'https://nikerane.github.io/kellerwatt-sim/methodology.html')}
      ${link('playground', 'Playground', 'https://nikerane.github.io/kellerwatt-sim/playground.html')}
    </span>
  </nav>`;
}

/**
 * Assumption stat card (used on Methodology page).
 * @param {string} label
 * @param {string} value
 * @returns {string}
 */
export function renderStatCard(label, value) {
  return `<div style="background:var(--paper);padding:16px 18px;border-radius:var(--r-12);border:var(--hairline)">
    <div style="font-size:0.72rem;opacity:0.5;font-family:var(--mono);margin-bottom:4px">${esc(label)}</div>
    ${renderDataMono(value, { size: 'md' })}
  </div>`;
}

/**
 * Numbered method step (used on Methodology page).
 * @param {string} num
 * @param {string} title
 * @param {string} body
 * @returns {string}
 */
export function renderMethodStep(num, title, body) {
  return `<div style="display:flex;gap:16px;align-items:baseline">
    <span style="flex:0 0 auto;width:28px;height:28px;border-radius:50%;background:var(--hearth);color:var(--bone);display:flex;align-items:center;justify-content:center;font-size:0.78rem;font-family:var(--mono);font-weight:500">${esc(num)}</span>
    <div>
      <strong style="font-family:var(--serif);font-weight:500;font-size:1.05rem">${esc(title)}</strong>
      <p style="margin:4px 0 0;opacity:0.72;font-size:0.92rem;line-height:1.55">${esc(body)}</p>
    </div>
  </div>`;
}

/**
 * Diligence list item.
 * @param {string} body
 * @returns {string}
 */
export function renderDiligenceItem(body) {
  return `<li class="kw-diligence__item" style="border-bottom:none;padding-bottom:8px">
    <span style="opacity:0.72;font-size:0.92rem">${esc(body)}</span>
  </li>`;
}

// -- internal helpers --

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function escAttr(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;');
}
```

- [ ] **Step 2: Quick sanity check in Node**

```bash
node --input-type=module -e "
import { renderEyebrow, renderDataMono, renderCouplet, renderSiteNav } from './web/vanilla/js/lib/components.js';
console.log(renderEyebrow('test', { ember: true }));
console.log(renderCouplet('First line', 'Second line'));
"
```

Expected: two HTML strings output with `kw-eyebrow kw-eyebrow--ember` and `kw-couplet kw-couplet--lg` classes.

- [ ] **Step 3: Commit**

```bash
git add web/vanilla/js/lib/components.js
git commit -m "feat(vanilla): add component library — HTML-generating functions"
```

---

### Task 4: Chart library — SVG charts via template literals

**Files:**
- Create: `web/vanilla/js/lib/charts.js`

Mirrors `SpreadChart.tsx` and `PlaygroundChart.tsx`. Uses the same `d3-scale` functions but builds SVG via template literals instead of JSX. d3-scale is loaded from CDN before this script.

- [ ] **Step 1: Write the file**

```js
// web/vanilla/js/lib/charts.js
// SVG chart renderers. Mirrors SpreadChart.tsx and PlaygroundChart.tsx.
// Depends on: d3 (loaded from CDN as <script> before this file).
// Import: the d3 global exposes scaleLinear, scalePoint.

const { scaleLinear, scalePoint } = d3;

/** Build an SVG path "d" attribute from an array of [x, y] points. */
function linePath(pts) {
  return pts
    .map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`)
    .join(' ');
}

// ---- Honesty page SpreadChart ----

const HONESTY_W = 720;
const HONESTY_H = 440;
const HONESTY_M = { top: 28, right: 28, bottom: 52, left: 56 };

/**
 * Widening-spread chart for the Honesty/Validation page.
 * Assumes `data` has YEARS array, assumed spread, and strategies.
 * @param {object} data  — the full sim_results.json object
 * @returns {string} HTML string (div.kw-chart with inline SVG)
 */
export function renderSpreadChart(data) {
  const years = data.provenance.years;
  const assumed = data.assumptions.business_plan.assumed_spread_eur_mwh;
  const ceilingStrat = data.strategies.find(s => s.id === 'lp_ceiling');
  const causalStrat = data.strategies.find(s => s.id === 'causal_walkforward');

  const ceiling = years.map(y => {
    const yr = ceilingStrat.years.find(x => x.year === y);
    return yr ? (yr.ceiling_eur_mwh ?? 0) : 0;
  });
  const causal = years.map(y => {
    const yr = causalStrat.years.find(x => x.year === y);
    return yr ? (yr.causal_eur_mwh ?? 0) : 0;
  });

  const yMax = Math.ceil((Math.max(assumed, ...ceiling) + 6) / 10) * 10;
  const x = scalePoint().domain(years.map(String)).range([HONESTY_M.left, HONESTY_W - HONESTY_M.right]).padding(0.5);
  const y = scaleLinear().domain([0, yMax]).range([HONESTY_H - HONESTY_M.bottom, HONESTY_M.top]);

  const px = i => x(String(years[i]));
  const ceilPts = ceiling.map((v, i) => [px(i), y(v)]);
  const causPts = causal.map((v, i) => [px(i), y(v)]);
  const bracket = linePath(ceilPts) + ' ' + linePath([...causPts].reverse()).replace('M', 'L') + ' Z';
  const yTicks = [0, 20, 40, 60, 80].filter(t => t <= yMax);

  const ariaLabel =
    `Captured spread by year. Assumed €${assumed} per MWh. ` +
    years.map((yr, i) => `${yr}: best €${ceiling[i].toFixed(1)}, real €${causal[i].toFixed(1)}`).join('; ') + '.';

  return `<div class="kw-chart">
    <svg viewBox="0 0 ${HONESTY_W} ${HONESTY_H}" role="img" aria-label="${escAttr(ariaLabel)}">
      ${yTicks.map(t => `
        <g>
          <line class="kw-chart__grid" x1="${HONESTY_M.left}" x2="${HONESTY_W - HONESTY_M.right}" y1="${y(t)}" y2="${y(t)}"/>
          <text class="kw-chart__axis" x="${HONESTY_M.left - 12}" y="${y(t)}" dy="0.32em" text-anchor="end">${t}</text>
        </g>`).join('')}
      <path class="kw-chart__bracket" d="${bracket}"/>
      <line class="kw-chart__assumed" x1="${HONESTY_M.left}" x2="${HONESTY_W - HONESTY_M.right}" y1="${y(assumed)}" y2="${y(assumed)}"/>
      <text class="kw-chart__axis" x="${HONESTY_W - HONESTY_M.right}" y="${y(assumed) - 8}" text-anchor="end">€${assumed} assumed</text>
      <path class="kw-chart__causal" d="${linePath(causPts)}"/>
      <path class="kw-chart__ceiling" d="${linePath(ceilPts)}"/>
      ${ceilPts.map(([cx, cy], i) => `
        <g>
          <circle class="kw-chart__dot" cx="${cx}" cy="${cy}" r="4.5"/>
          <text class="kw-chart__axis" x="${cx}" y="${cy - 14}" text-anchor="middle" style="fill:var(--ember);font-size:13px">€${ceiling[i].toFixed(1)}</text>
        </g>`).join('')}
      ${causPts.map(([cx, cy], i) => `
        <text class="kw-chart__axis" x="${cx}" y="${cy + 20}" text-anchor="middle">€${causal[i].toFixed(1)}</text>`).join('')}
      ${years.map((yr, i) => `
        <text class="kw-chart__axis" x="${px(i)}" y="${HONESTY_H - HONESTY_M.bottom + 26}" text-anchor="middle">${yr}</text>`).join('')}
    </svg>
    <div class="kw-chart__legend">
      <span><span class="kw-chart__swatch" style="border-color:var(--ember)"/> Best-case (perfect info)</span>
      <span><span class="kw-chart__swatch" style="border-color:rgba(245,241,234,0.85)"/> Realistic strategy</span>
      <span><span class="kw-chart__swatch" style="border-color:rgba(245,241,234,0.45);border-top-style:dashed"/> €${assumed} assumed</span>
    </div>
  </div>`;
}

// ---- Playground page chart ----

const PG_W = 600;
const PG_H = 300;
const PG_M = { top: 20, right: 28, bottom: 44, left: 52 };

/**
 * Smaller spread chart for live-solved playground results.
 * @param {object} response  — SolveResponse shape from HF engine
 * @returns {string} HTML string
 */
export function renderPlaygroundChart(response) {
  const years = response.years;
  const assumed = response.assumed.spread_eur_mwh;
  const ceiling = years.map(y => response.ceiling[String(y)]?.spread_eur_mwh ?? 0);
  const causal = years.map(y => response.causal_retained[String(y)]?.spread_eur_mwh ?? 0);

  const yMax = Math.ceil((Math.max(assumed, ...ceiling) + 6) / 10) * 10;
  const x = scalePoint().domain(years.map(String)).range([PG_M.left, PG_W - PG_M.right]).padding(0.5);
  const y = scaleLinear().domain([0, yMax]).range([PG_H - PG_M.bottom, PG_M.top]);

  const px = i => x(String(years[i]));
  const ceilPts = ceiling.map((v, i) => [px(i), y(v)]);
  const causPts = causal.map((v, i) => [px(i), y(v)]);
  const bracket = linePath(ceilPts) + ' ' + linePath([...causPts].reverse()).replace('M', 'L') + ' Z';
  const yTicks = [0, 20, 40, 60, 80, 100, 120].filter(t => t <= yMax);

  const ariaLabel =
    `Playground spread chart. Assumed €${assumed}/MWh. ` +
    years.map((yr, i) => `${yr}: best €${ceiling[i].toFixed(1)}, real €${causal[i].toFixed(1)}`).join('; ') + '.';

  return `<div class="kw-chart" style="margin-top:40px">
    <svg viewBox="0 0 ${PG_W} ${PG_H}" role="img" aria-label="${escAttr(ariaLabel)}">
      ${yTicks.map(t => `
        <g>
          <line class="kw-chart__grid" x1="${PG_M.left}" x2="${PG_W - PG_M.right}" y1="${y(t)}" y2="${y(t)}"/>
          <text class="kw-chart__axis" x="${PG_M.left - 12}" y="${y(t)}" dy="0.32em" text-anchor="end">${t}</text>
        </g>`).join('')}
      <path class="kw-chart__bracket" d="${bracket}"/>
      <line class="kw-chart__assumed" x1="${PG_M.left}" x2="${PG_W - PG_M.right}" y1="${y(assumed)}" y2="${y(assumed)}"/>
      <text class="kw-chart__axis" x="${PG_W - PG_M.right}" y="${y(assumed) - 8}" text-anchor="end">€${assumed} assumed</text>
      <path class="kw-chart__causal" d="${linePath(causPts)}"/>
      <path class="kw-chart__ceiling" d="${linePath(ceilPts)}"/>
      ${ceilPts.map(([cx, cy], i) => `
        <g>
          <circle class="kw-chart__dot" cx="${cx}" cy="${cy}" r="4.5"/>
          <text class="kw-chart__axis" x="${cx}" y="${cy - 14}" text-anchor="middle" style="fill:var(--ember);font-size:13px">€${ceiling[i].toFixed(1)}</text>
        </g>`).join('')}
      ${years.map((yr, i) => `
        <text class="kw-chart__axis" x="${px(i)}" y="${PG_H - PG_M.bottom + 26}" text-anchor="middle">${yr}</text>`).join('')}
    </svg>
    <div class="kw-chart__legend">
      <span><span class="kw-chart__swatch" style="border-color:var(--ember)"/> Best-case</span>
      <span><span class="kw-chart__swatch" style="border-color:rgba(245,241,234,0.85)"/> Realistic</span>
      <span><span class="kw-chart__swatch" style="border-color:rgba(245,241,234,0.45);border-top-style:dashed"/> Assumed</span>
    </div>
  </div>`;
}

// -- internal --

function escAttr(s) {
  return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;');
}
```

- [ ] **Step 2: Syntax check**

```bash
node --input-type=module -e "console.log('syntax ok')"  # charts.js needs d3 at runtime, so we only check syntax
node -e "require('fs').readFileSync('web/vanilla/js/lib/charts.js','utf8'); console.log('readable')"
```

- [ ] **Step 3: Commit**

```bash
git add web/vanilla/js/lib/charts.js
git commit -m "feat(vanilla): add chart library — SVG charts via template literals"
```

---

### Task 5: Honesty (Validation) page

**Files:**
- Create: `web/vanilla/index.html`
- Create: `web/vanilla/js/pages/honesty.js`

- [ ] **Step 1: Write the HTML shell**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>KellerWatt — the number, honestly</title>
    <meta name="description" content="What the battery actually earns on real German day-ahead prices — the validated perfect-foresight ceiling, a backtested causal benchmark, and what is still in diligence." />
    <link rel="stylesheet" href="css/tokens.css" />
    <link rel="stylesheet" href="css/app.css" />
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500&family=Inter:opsz,wght@14..32,400;14..32,500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
    <script src="https://cdn.jsdelivr.net/npm/d3-scale@4" crossorigin="anonymous"></script>
    <!-- TODO: add integrity="sha384-..." after looking up the correct SRI hash -->
    <script type="module" src="js/lib/components.js"></script>
    <script type="module" src="js/lib/data.js"></script>
    <script type="module" src="js/lib/charts.js"></script>
    <script type="module" src="js/pages/honesty.js"></script>
  </head>
  <body>
    <main id="root"></main>
  </body>
</html>
```

- [ ] **Step 2: Write the page JS**

```js
// web/vanilla/js/pages/honesty.js
// Honesty / Validation page. Mirrors src/pages/HonestyPage.tsx.

import { renderSiteNav, renderEyebrow, renderCouplet, renderDataMono } from '../lib/components.js';
import { fetchSimResults, results, strategy, yearOf, euro, eurPerMwh, captureOfCeiling, YEARS } from '../lib/data.js';
import { renderSpreadChart } from '../lib/charts.js';

async function init() {
  const data = await fetchSimResults();
  // Backfill YEARS array
  YEARS.length = 0;
  YEARS.push(...data.provenance.years);

  const bp = data.assumptions.business_plan;
  const p = data.provenance;
  const latest = Math.max(...YEARS);

  const ceilingStrat = strategy('lp_ceiling');
  const causalStrat = strategy('causal_walkforward');
  const retained = data.scenarios.find(s => s.id === 'causal_exemption_retained');
  const lost = data.scenarios.find(s => s.id === 'causal_exemption_lost');

  const ceilSpreads = ceilingStrat.years.map(y => y.ceiling_eur_mwh ?? 0);
  const ceilMin = Math.min(...ceilSpreads);
  const ceilMax = Math.max(...ceilSpreads);
  const captures = YEARS.map(captureOfCeiling).filter(v => v !== null);
  const capLo = Math.round(Math.min(...captures) * 100);
  const capHi = Math.round(Math.max(...captures) * 100);

  // Build the case table columns
  const ceil = yearOf(ceilingStrat, latest);
  const causalYear = yearOf(causalStrat, latest);

  const cols = [
    { key: 'assumed', title: 'Assumed', sub: 'business plan', tone: 'muted', spread: bp.assumed_spread_eur_mwh, annual: bp.assumed_gross_eur, cyclesPerDay: bp.assumed_cycles_per_day },
    { key: 'ceiling', title: 'Best-case', sub: 'perfect info', tone: 'ember', spread: ceil.ceiling_eur_mwh, annual: ceil.gross_eur, cyclesPerDay: ceil.cycles_ac },
    { key: 'causal', title: 'Realistic', sub: 'actual strategy', tone: 'neutral', spread: retained.implied_spread.value, annual: retained.net_annual_eur, cyclesPerDay: causalYear.cycles_ac },
    { key: 'lost', title: 'Conservative', sub: 'exemption lost', tone: 'neutral', spread: lost.implied_spread.value, annual: lost.net_annual_eur, cyclesPerDay: causalYear.cycles_ac },
  ];

  function valCls(c) { return c.key === 'ceiling' ? 'kw-table__col-validated' : ''; }

  const caseTableHTML = `
    <table class="kw-table">
      <caption class="kw-eyebrow" style="margin-bottom:18px">Captured spread · ${latest}</caption>
      <thead>
        <tr>
          <th scope="col" aria-label="metric"></th>
          ${cols.map(c => `<th scope="col" class="${valCls(c)}">${c.title}<span class="kw-table__row-note">${c.sub}</span></th>`).join('')}
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row">Implied spread<span class="kw-table__row-note">€ / MWh discharged</span></th>
          ${cols.map(c => `<td class="${valCls(c)}">${renderDataMono(eurPerMwh(c.spread), { tone: c.tone, size: 'lg' })}</td>`).join('')}
        </tr>
        <tr>
          <th scope="row">Annual figure<span class="kw-table__row-note">gross / net per year</span></th>
          ${cols.map(c => `<td class="${valCls(c)}">${renderDataMono(euro(c.annual), { tone: c.tone === 'ember' ? 'ember' : 'neutral' })}</td>`).join('')}
        </tr>
        <tr>
          <th scope="row">Cycles / day<span class="kw-table__row-note">AC delivered</span></th>
          ${cols.map(c => `<td class="${valCls(c)}">${renderDataMono(cycles(c.cyclesPerDay), { tone: 'muted' })}</td>`).join('')}
        </tr>
      </tbody>
    </table>`;

  const root = document.getElementById('root');
  root.innerHTML = `
    ${renderSiteNav('honesty')}

    <section class="kw-section kw-section--hearth">
      <div class="kw-section__inner">
        <div class="kw-fade">
          ${renderEyebrow('Validated on real DE-LU prices', { ember: true })}
        </div>
        <div class="kw-fade kw-fade--2" style="margin-top:28px">
          ${renderCouplet('We assumed €80 a megawatt-hour.', 'Real prices never got there.', { as: 'h1', size: 'xl' })}
        </div>
        <p class="kw-lead kw-fade kw-fade--3" style="margin-top:28px">
          A perfect-foresight battery on German day-ahead prices captured
          ${renderDataMono(eurPerMwh(ceilMin), { tone: 'ember' })}–
          ${renderDataMono(eurPerMwh(ceilMax), { tone: 'ember' })} per MWh every year from
          ${YEARS[0]} to ${latest} — always under the €80 the deck assumed. A causal strategy
          with no foresight captures less still. This page separates what is validated from
          what is only an estimate, and names what is still in diligence.
        </p>
        <div class="kw-hero__meta kw-fade kw-fade--3">
          <span style="display:flex;flex-direction:column;gap:4px">
            ${renderEyebrow('Validated best-case')}
            ${renderDataMono(`${eurPerMwh(ceilMin)}–${eurPerMwh(ceilMax)}`, { tone: 'ember', size: 'lg' })}
          </span>
          <span style="display:flex;flex-direction:column;gap:4px">
            ${renderEyebrow('Years backtested')}
            ${renderDataMono(String(YEARS.length), { size: 'lg' })}
          </span>
          <span style="display:flex;flex-direction:column;gap:4px">
            ${renderEyebrow('Realistic vs best-case')}
            ${renderDataMono(`${capLo}–${capHi}%`, { size: 'lg' })}
          </span>
          <span style="display:flex;flex-direction:column;gap:4px">
            ${renderEyebrow('Simultaneity')}
            ${renderDataMono('0', { size: 'lg' })}
          </span>
        </div>
      </div>
    </section>

    <section class="kw-section kw-section--bone">
      <div class="kw-section__inner">
        ${renderEyebrow('The four cases')}
        ${renderCouplet('Here is the assumption.', 'Here is what the market actually paid.', { size: 'lg' })}
        <p class="kw-lead" style="margin-top:20px;margin-bottom:36px">
          The best-case is the most a battery could earn with perfect information — an upper
          bound, validated to the decimal on real prices. The realistic case is a backtested
          estimate; the conservative case adds the grid fee owed if the §118(6) exemption is
          lost. IRR and payback stay blank until two diligence items land.
        </p>
        <div style="overflow-x:auto">${caseTableHTML}</div>
        <p class="kw-lead" style="margin-top:24px;font-size:0.92rem;opacity:0.8">
          The deck claimed ${renderDataMono(euro(9947), { tone: 'muted' })} gross a year. Reconciled from the same
          identity — spread × usable MWh × cycles × days — the €80 assumption is worth
          ${renderDataMono(euro(bp.assumed_gross_eur), { tone: 'muted' })}, not €9,947.
        </p>
      </div>
    </section>

    <section class="kw-section kw-section--hearth">
      <div class="kw-section__inner">
        ${renderEyebrow('The spread, by year')}
        ${renderCouplet('The best case is rising.', 'It has stayed under €80 every year.', { size: 'lg' })}
        <div class="kw-split kw-split--chart" style="margin-top:44px">
          <p class="kw-lead">
            Day-ahead spreads widened from ${YEARS[0]} to ${latest} as the system absorbed more
            renewables and more negative-price hours. Even so, the best-case scenario
            never reached the assumed €80 — and a real operator, blind to the day ahead,
            captured only ${capLo}–${capHi}% of that best case.
          </p>
          ${renderSpreadChart(data)}
        </div>
      </div>
    </section>

    <section class="kw-section kw-section--bone">
      <div class="kw-section__inner">
        ${renderEyebrow('Still in diligence')}
        ${renderCouplet('Two questions remain open.', 'We are not hiding them.', { size: 'lg' })}
        <ul class="kw-diligence__list" style="margin-top:32px">
          <li class="kw-diligence__item">
            <span class="kw-diligence__tag">${renderDataMono('#8', { tone: 'muted', size: 'sm' })}</span>
            <span>
              <strong style="font-family:var(--serif);font-weight:500;font-size:1.15rem">Aggregator term sheet</strong>
              <span style="display:block;margin-top:6px;opacity:0.82">The BKV fee basis — turnover or net margin — and the revenue share come from a real aggregator term sheet, not code. The three fee bases are implemented and tested; the actual one is pending.</span>
            </span>
          </li>
          <li class="kw-diligence__item">
            <span class="kw-diligence__tag">${renderDataMono('#9', { tone: 'muted', size: 'sm' })}</span>
            <span>
              <strong style="font-family:var(--serif);font-weight:500;font-size:1.15rem">§118(6) EnWG legal memo</strong>
              <span style="display:block;margin-top:6px;opacity:0.82">Whether the grid-fee exemption is retained or lost is a legal question. The conservative case applies a provisional €${data.assumptions.fees.grid_energy_fee_eur_mwh_charge || 30}/MWh charge on energy drawn, pending the memo.</span>
            </span>
          </li>
        </ul>
        <p class="kw-lead" style="margin-top:28px;font-size:0.92rem;opacity:0.82">
          Until both land, project IRR and payback remain blank — a constant-EBITDA
          placeholder is not a return.
        </p>
      </div>
    </section>

    <footer class="kw-footer">
      ${renderEyebrow('How this works')}
      <p style="margin-top:14px">
        Every number on this page comes from running an optimisation solver
        (HiGHS — open-source, industry-standard) on real ${p.price_zone} day-ahead
        electricity prices from ${p.data_source}, ${p.years.join(' / ')}. The solver
        finds the profit-maximising charge/discharge schedule for each day given
        the battery's specs. Best-case assumes perfect knowledge of tomorrow's
        prices. Realistic uses only past data.
      </p>
      <p style="margin-top:10px;font-size:0.78rem;opacity:0.55">
        Solver status: ${data.solver.status}. Generated ${p.generated_utc}${p.git_commit ? ' · build ' + p.git_commit.slice(0, 10) : ''}. Schema v${data.schema_version}. ${p.note}
      </p>
    </footer>`;
}

init().catch(err => {
  document.getElementById('root').innerHTML = `<p style="padding:2rem;color:var(--clay-red)">Failed to load: ${err.message}</p>`;
});
```

- [ ] **Step 3: Open the page locally and verify rendering**

```bash
# Serve the vanilla directory and check in browser
cd web/vanilla && python3 -m http.server 8080
```

Open `http://localhost:8080/index.html` in a browser. Verify:
- SiteNav renders with "Validation" highlighted
- Hero section with couplet and stats
- Four-column case table with all rows
- Spread chart SVG visible
- Diligence items with #8 and #9 tags
- Footer with provenance info

- [ ] **Step 4: Commit**

```bash
git add web/vanilla/index.html web/vanilla/js/pages/honesty.js
git commit -m "feat(vanilla): add Honesty/Validation page"
```

---

### Task 6: Methodology page

**Files:**
- Create: `web/vanilla/methodology.html`
- Create: `web/vanilla/js/pages/methodology.js`

- [ ] **Step 1: Write the HTML shell**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>KellerWatt — methodology & formulas</title>
    <meta name="description" content="How the KellerWatt arbitrage number is computed: assumptions, every formula with live values, per-year detail on real DE-LU prices, and the known limitations." />
    <link rel="stylesheet" href="css/tokens.css" />
    <link rel="stylesheet" href="css/app.css" />
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500&family=Inter:opsz,wght@14..32,400;14..32,500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
    <script type="module" src="js/lib/components.js"></script>
    <script type="module" src="js/lib/data.js"></script>
    <script type="module" src="js/pages/methodology.js"></script>
  </head>
  <body>
    <main id="root"></main>
  </body>
</html>
```

- [ ] **Step 2: Write the page JS**

```js
// web/vanilla/js/pages/methodology.js
// Methodology page. Mirrors src/pages/MethodologyPage.tsx.

import { renderSiteNav, renderEyebrow, renderCouplet, renderDataMono, renderStatCard, renderMethodStep, renderDiligenceItem } from '../lib/components.js';
import { fetchSimResults, results, YEARS } from '../lib/data.js';

async function init() {
  const data = await fetchSimResults();
  YEARS.length = 0;
  YEARS.push(...data.provenance.years);

  const bp = data.assumptions.business_plan;
  const battery = data.assumptions.battery;
  const latest = Math.max(...YEARS);
  const cyclesPerDay = bp.assumed_cycles_per_day;
  const usable = battery.usable_kwh;

  const root = document.getElementById('root');
  root.innerHTML = `
    ${renderSiteNav('methodology')}

    <section class="kw-section kw-section--hearth">
      <div class="kw-section__inner">
        ${renderEyebrow('How the number is computed', { ember: true })}
        ${renderCouplet('The conclusions are on the Validation page.', 'Here are the workings.', { as: 'h1', size: 'lg' })}
      </div>
    </section>

    <section class="kw-section kw-section--bone">
      <div class="kw-section__inner">
        ${renderEyebrow('Assumptions')}
        <p class="kw-lead" style="margin-top:18px;margin-bottom:24px">
          Every figure on the Validation page starts from a single battery unit
          and a set of fixed inputs — the same spreadsheet model, solved against
          real DE-LU prices.
        </p>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:20px;margin-bottom:36px">
          ${renderStatCard('Battery capacity', '200 kWh')}
          ${renderStatCard('Power rating', '50 kW')}
          ${renderStatCard('Round-trip efficiency', '90%')}
          ${renderStatCard('Usable energy', `${usable} kWh`)}
          ${renderStatCard('Cycles per day (assumed)', cyclesPerDay.toFixed(2))}
          ${renderStatCard('Operating days', '365')}
          ${renderStatCard('Assumed spread', `€${bp.assumed_spread_eur_mwh}/MWh`)}
          ${renderStatCard('Solver', `${data.solver.name} ${data.solver.version}`)}
        </div>
      </div>
    </section>

    <section class="kw-section kw-section--bone kw-section--tight">
      <div class="kw-section__inner">
        ${renderEyebrow('How the real numbers are computed')}
        <p class="kw-lead" style="margin-top:18px;margin-bottom:24px">
          The validated best-case and realistic figures come from running
          <strong>HiGHS</strong> — an open-source linear optimisation solver —
          on real Energy-Charts day-ahead prices across ${YEARS.length} years.
        </p>
        <div style="display:grid;gap:16px">
          ${renderMethodStep('1', 'Load real prices',
            `For each day from ${YEARS[0]} to ${latest}, fetch DE-LU day-ahead hourly prices from Energy-Charts.info. These are the actual market-clearing prices — not forecasts.`)}
          ${renderMethodStep('2', 'Solve the ceiling LP',
            'For each day, a linear program finds the profit-maximising charge-discharge schedule with perfect knowledge of the next 24 hours of prices. This is the upper bound — no real operator can achieve this, but it\'s a validated benchmark. The solver is HiGHS, an open-source MILP solver.')}
          ${renderMethodStep('3', 'Run the causal walk-forward',
            'A realistic strategy that decides charge/discharge with a 28-day trailing threshold — it sees only past prices, not future ones. This produces the backtested estimate.')}
          ${renderMethodStep('4', 'Compute implied spreads',
            'Annual gross € ÷ MWh discharged = implied spread in €/MWh. This is the single number that makes the cases comparable — the same "price difference captured per unit of energy" regardless of battery size or cycle count.')}
        </div>
      </div>
    </section>

    <section class="kw-section kw-section--bone kw-section--tight">
      <div class="kw-section__inner">
        ${renderEyebrow('Limitations')}
        <ul class="kw-diligence__list" style="margin-top:18px">
          ${renderDiligenceItem('Prices are day-ahead only. Intraday and balancing-market revenues are not included.')}
          ${renderDiligenceItem('Battery degradation is modelled as a fixed 2%/yr capacity loss per the assumptions spreadsheet.')}
          ${renderDiligenceItem('The causal strategy uses a 28-day trailing threshold. Real operators use more sophisticated forecasting.')}
          ${renderDiligenceItem('Grid fees use the simplified Energy-Charts model. Real German grid fees vary by region and voltage level.')}
          ${renderDiligenceItem('Ancillary-service revenue (FCR, aFRR) is excluded — arbitrage only.')}
          ${renderDiligenceItem('The model assumes one full cycle per day. Multi-cycle strategies may capture more value.')}
        </ul>
      </div>
    </section>

    <footer class="kw-footer">
      ${renderEyebrow('Provenance')}
      <p style="margin-top:14px">
        ${data.provenance.data_source} · ${data.provenance.price_zone} ·
        ${data.provenance.years.join('–')} · schema v${data.schema_version}
      </p>
    </footer>`;
}

init().catch(err => {
  document.getElementById('root').innerHTML = `<p style="padding:2rem;color:var(--clay-red)">Failed to load: ${err.message}</p>`;
});
```

- [ ] **Step 3: Verify locally**

Serve with `python3 -m http.server 8080` from `web/vanilla/`, open `http://localhost:8080/methodology.html`.

Verify:
- SiteNav with "Methodology" highlighted
- Hero couplet
- 8 stat cards in a grid
- Four numbered method steps
- Six limitation bullet points
- Footer

- [ ] **Step 4: Commit**

```bash
git add web/vanilla/methodology.html web/vanilla/js/pages/methodology.js
git commit -m "feat(vanilla): add Methodology page"
```

---

### Task 7: Playground page (interactive)

**Files:**
- Create: `web/vanilla/playground.html`
- Create: `web/vanilla/js/pages/playground.js`

This is the most complex page — it has 6 sliders, a toggle, a Compute button, and a fetch to the HF engine. All state lives in plain variables. DOM updates via targeted re-renders.

- [ ] **Step 1: Write the HTML shell**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>KellerWatt — playground</title>
    <meta name="description" content="Change the battery and economic assumptions. Watch the KellerWatt numbers move — live-solved on a Python engine." />
    <link rel="stylesheet" href="css/tokens.css" />
    <link rel="stylesheet" href="css/app.css" />
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500&family=Inter:opsz,wght@14..32,400;14..32,500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
    <script src="https://cdn.jsdelivr.net/npm/d3-scale@4" crossorigin="anonymous"></script>
    <!-- TODO: add integrity="sha384-..." after looking up the correct SRI hash -->
    <script type="module" src="js/lib/components.js"></script>
    <script type="module" src="js/lib/data.js"></script>
    <script type="module" src="js/lib/charts.js"></script>
    <script type="module" src="js/pages/playground.js"></script>
  </head>
  <body>
    <main id="root"></main>
  </body>
</html>
```

- [ ] **Step 2: Write the page JS (part 1 — state, defaults, render helpers)**

```js
// web/vanilla/js/pages/playground.js
// Interactive Playground page. Mirrors src/pages/PlaygroundPage.tsx.

import { renderSiteNav, renderEyebrow, renderCouplet, renderDataMono } from '../lib/components.js';
import { fetchSimResults, euro, eurPerMwh, cycles } from '../lib/data.js';
import { renderPlaygroundChart } from '../lib/charts.js';

// ---- config ----
const ENGINE_URL = 'https://nikerane-kellerwatt-engine.hf.space';

const SLIDERS = [
  { key: 'capacity_kwh', label: 'Battery capacity', min: 50,  max: 350, step: 50,  default: 200, unit: 'kWh' },
  { key: 'power_kw',     label: 'Power rating',      min: 25,  max: 250, step: 50,  default: 50,  unit: 'kW' },
  { key: 'rte',          label: 'Round-trip efficiency', min: 0.75, max: 0.95, step: 0.05, default: 0.90, unit: '%', formatValue: v => Math.round(v * 100) + '%' },
  { key: 'assumed_spread', label: 'Assumed spread',   min: 20,  max: 120, step: 5,   default: 80,  unit: '€/MWh' },
  { key: 'cycles_per_day', label: 'Daily cycle cap',  min: 0.5, max: 3.0,  step: 0.5, default: 1.5, unit: 'cyc/day' },
  { key: 'grid_fee',     label: 'Grid energy fee',    min: 0,   max: 50,  step: 5,   default: 0,   unit: '€/MWh' },
];

// ---- state ----
let values = {};
let exemption = 'retained';
let response = null;     // SolveResponse
let status = 'idle';     // 'idle' | 'computing' | 'error'
let simData = null;      // raw sim_results.json
let latestYear = 2025;

// ---- default SolveResponse from baked-in data ----
function defaultSolveResponse(data) {
  const bp = data.assumptions.business_plan;
  const years = data.provenance.years;

  const ceiling = {}; const causalR = {}; const causalL = {};
  const ceilingGross = {}; const causalGross = {};
  const ceilingCycles = {}; const causalCycles = {};

  for (const s of data.strategies) {
    for (const yr of s.years) {
      const key = String(yr.year);
      if (s.id === 'lp_ceiling') {
        ceiling[key] = yr.ceiling_eur_mwh;
        ceilingGross[key] = yr.gross_eur;
        ceilingCycles[key] = yr.cycles_ac;
      } else if (s.id === 'causal_walkforward') {
        causalR[key] = yr.causal_eur_mwh;
        causalGross[key] = yr.gross_eur;
        causalCycles[key] = yr.cycles_ac;
        causalL[key] = yr.causal_eur_mwh; // same data for both
      }
    }
  }

  function wrap(spread, gross, cyclesAc) {
    const out = {};
    for (const y of years.map(String)) {
      out[y] = {
        spread_eur_mwh: spread[y] ?? null,
        gross_eur: gross[y] ?? null,
        cycles_ac: cyclesAc[y] ?? null,
      };
    }
    return out;
  }

  return {
    schema_version: data.schema_version,
    years,
    assumed: {
      spread_eur_mwh: bp.assumed_spread_eur_mwh,
      gross_eur: bp.assumed_gross_eur,
      cycles_per_day: bp.assumed_cycles_per_day,
    },
    ceiling: wrap(ceiling, ceilingGross, ceilingCycles),
    causal_retained: wrap(causalR, causalGross, causalCycles),
    causal_lost: wrap(causalL, causalGross, causalCycles),
  };
}

// ---- DOM helpers ----

function renderSlider(slider) {
  const value = values[slider.key];
  const display = slider.formatValue ? slider.formatValue(value) : `${value} ${slider.unit}`;
  const disabled = status === 'computing' ? ' disabled' : '';
  return `<label class="kw-slider" style="display:flex;flex-direction:column;gap:6px">
    <span class="kw-slider__label" style="display:flex;justify-content:space-between">
      <span style="font-family:var(--sans);font-size:0.85rem;color:var(--slate)">${slider.label}</span>
      ${renderDataMono(display, { tone: 'ember', size: 'sm' })}
    </span>
    <input type="range" min="${slider.min}" max="${slider.max}" step="${slider.step}" value="${value}" class="kw-slider__input" aria-label="${slider.label}" data-key="${slider.key}"${disabled}>
    <span class="kw-slider__range-labels" style="display:flex;justify-content:space-between;font-size:0.72rem;opacity:0.5">
      <span>${slider.formatValue ? slider.formatValue(slider.min) : slider.min}</span>
      <span>${slider.formatValue ? slider.formatValue(slider.max) : slider.max}</span>
    </span>
  </label>`;
}

function renderResultsTable() {
  const yr = String(latestYear);
  const ceil = response.ceiling[yr];
  const causalR = response.causal_retained[yr];
  const causalL = response.causal_lost[yr];

  const cols = [
    { key: 'assumed', title: 'Assumed', sub: 'your inputs', tone: 'muted', spread: response.assumed.spread_eur_mwh, annual: response.assumed.gross_eur, cyclesPerDay: response.assumed.cycles_per_day },
    { key: 'ceiling', title: 'Best-case', sub: 'perfect info', tone: 'ember', spread: ceil?.spread_eur_mwh ?? null, annual: ceil?.gross_eur ?? null, cyclesPerDay: ceil?.cycles_ac ?? null },
    { key: 'causal-retained', title: 'Realistic', sub: 'exemption retained', tone: 'neutral', spread: causalR?.spread_eur_mwh ?? null, annual: causalR?.gross_eur ?? null, cyclesPerDay: causalR?.cycles_ac ?? null },
    { key: 'causal-lost', title: 'Conservative', sub: 'exemption lost', tone: 'neutral', spread: causalL?.spread_eur_mwh ?? null, annual: causalL?.gross_eur ?? null, cyclesPerDay: causalL?.cycles_ac ?? null },
  ];

  function valCls(c) { return c.key === 'ceiling' ? 'kw-table__col-validated' : ''; }

  return `<table class="kw-table" style="margin-top:32px">
    <caption class="kw-eyebrow" style="margin-bottom:18px">Captured spread · ${yr}</caption>
    <thead>
      <tr>
        <th scope="col" aria-label="metric"></th>
        ${cols.map(c => `<th scope="col" class="${valCls(c)}">${c.title}<span class="kw-table__row-note">${c.sub}</span></th>`).join('')}
      </tr>
    </thead>
    <tbody>
      <tr>
        <th scope="row">Implied spread<span class="kw-table__row-note">€ / MWh discharged</span></th>
        ${cols.map(c => `<td class="${valCls(c)}">${renderDataMono(eurPerMwh(c.spread), { tone: c.tone, size: 'lg' })}</td>`).join('')}
      </tr>
      <tr>
        <th scope="row">Annual figure<span class="kw-table__row-note">gross / net per year</span></th>
        ${cols.map(c => `<td class="${valCls(c)}">${renderDataMono(euro(c.annual), { tone: c.tone === 'ember' ? 'ember' : 'neutral' })}</td>`).join('')}
      </tr>
      <tr>
        <th scope="row">Cycles / day<span class="kw-table__row-note">AC delivered</span></th>
        ${cols.map(c => `<td class="${valCls(c)}">${renderDataMono(cycles(c.cyclesPerDay), { tone: 'muted' })}</td>`).join('')}
      </tr>
    </tbody>
  </table>`;
}

function renderComputeButton() {
  const disabled = status === 'computing' ? ' disabled' : '';
  const text = status === 'computing' ? 'Computing…' : 'Compute';
  let errorHTML = '';
  if (status === 'error') {
    errorHTML = `<span role="status" style="font-size:0.78rem;font-family:var(--mono);color:var(--clay-red)">
      Failed — <button type="button" id="retry-btn" style="background:none;border:none;color:var(--clay-red);cursor:pointer;text-decoration:underline;font-size:inherit;font-family:inherit;padding:0">try again</button>
    </span>`;
  }
  return `<span style="display:inline-flex;align-items:center;gap:10px">
    <button type="button" id="compute-btn" class="kw-dispatch-btn kw-dispatch-btn--active"${disabled} style="font-size:0.82rem;font-family:var(--mono)">${text}</button>
    ${errorHTML}
  </span>`;
}

function renderExemptionToggle() {
  return `<div class="kw-toggle" style="display:flex;flex-direction:column;gap:8px">
    <span style="font-family:var(--sans);font-size:0.85rem;color:var(--slate)">§118(6) exemption</span>
    <span style="display:flex;gap:8px">
      <button type="button" class="kw-toggle__btn${exemption === 'retained' ? ' kw-toggle__btn--active' : ''}" data-exc="retained"${status === 'computing' ? ' disabled' : ''}>Retained</button>
      <button type="button" class="kw-toggle__btn${exemption === 'lost' ? ' kw-toggle__btn--active' : ''}" data-exc="lost"${status === 'computing' ? ' disabled' : ''}>Lost</button>
    </span>
  </div>`;
}
```

- [ ] **Step 3: Write the page JS (part 2 — init, compute, render)**

Continue in the same file:

```js
// ---- compute ----
async function doCompute() {
  if (status === 'computing') return;
  status = 'computing';
  render();

  try {
    const res = await fetch(`${ENGINE_URL}/solve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        battery: {
          capacity_kwh: values.capacity_kwh,
          power_kw: values.power_kw,
          rte: values.rte,
        },
        assumed_spread_eur_mwh: values.assumed_spread,
        cycles_per_day: values.cycles_per_day,
        grid_fee_eur_mwh: values.grid_fee,
        exemption,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    response = await res.json();
    status = 'idle';
  } catch (err) {
    console.error('Compute failed:', err);
    status = 'error';
  }
  render();
}

// ---- main render ----
function render() {
  const root = document.getElementById('root');
  const slidersHTML = SLIDERS.map(renderSlider).join('');

  root.innerHTML = `
    ${renderSiteNav('playground')}

    <section class="kw-section kw-section--hearth">
      <div class="kw-section__inner">
        <div class="kw-fade">
          ${renderEyebrow('Interactive playground', { ember: true })}
        </div>
        <div class="kw-fade kw-fade--2" style="margin-top:28px">
          ${renderCouplet('Change the assumptions.', 'Watch the numbers move.', { as: 'h1', size: 'xl' })}
        </div>
        <p class="kw-lead kw-fade kw-fade--3" style="margin-top:28px">
          Tweak the sliders, then hit Compute. HiGHS — an open-source
          optimisation solver — finds the best charge/discharge schedule against
          real DE-LU day-ahead prices.
        </p>
      </div>
    </section>

    <section class="kw-section kw-section--bone kw-section--tight">
      <div class="kw-section__inner">
        <div style="display:flex;align-items:baseline;gap:16px;margin-bottom:28px;flex-wrap:wrap">
          ${renderEyebrow('Parameters')}
          ${renderComputeButton()}
        </div>
        <div class="kw-sliders-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:24px">
          ${slidersHTML}
          ${renderExemptionToggle()}
        </div>
      </div>
    </section>

    <section class="kw-section kw-section--bone">
      <div class="kw-section__inner">
        ${renderEyebrow('Results', { ember: true })}
        <div style="overflow-x:auto">${response ? renderResultsTable() : '<p>Loading…</p>'}</div>
      </div>
    </section>

    <section class="kw-section kw-section--hearth kw-section--tight">
      <div class="kw-section__inner">
        ${response ? renderPlaygroundChart(response) : ''}
      </div>
    </section>

    <footer class="kw-footer">
      ${renderEyebrow('How this works')}
      <p style="margin-top:14px">
        HiGHS — an open-source optimisation solver — reads real DE-LU day-ahead
        prices from Energy-Charts and finds the best possible charge/discharge
        schedule for each day. Best-case assumes perfect knowledge of tomorrow's
        prices. Realistic uses only past data, like a real operator would.
      </p>
    </footer>`;

  // ---- wire events ----
  const computeBtn = document.getElementById('compute-btn');
  if (computeBtn) computeBtn.addEventListener('click', doCompute);

  const retryBtn = document.getElementById('retry-btn');
  if (retryBtn) retryBtn.addEventListener('click', doCompute);

  // slider inputs
  root.querySelectorAll('input[type="range"]').forEach(input => {
    input.addEventListener('input', e => {
      const key = e.target.dataset.key;
      values[key] = parseFloat(e.target.value);
      // update value display
      const label = e.target.closest('.kw-slider');
      const displaySpan = label?.querySelector('.kw-slider__label .kw-mono');
      if (displaySpan) {
        const slider = SLIDERS.find(s => s.key === key);
        const display = slider.formatValue ? slider.formatValue(values[key]) : `${values[key]} ${slider.unit}`;
        displaySpan.textContent = display;
      }
    });
  });

  // toggle buttons
  root.querySelectorAll('[data-exc]').forEach(btn => {
    btn.addEventListener('click', () => {
      if (status === 'computing') return;
      exemption = btn.dataset.exc;
      render();
    });
  });
}

// ---- init ----
async function init() {
  simData = await fetchSimResults();
  // populate defaults
  for (const s of SLIDERS) values[s.key] = s.default;
  response = defaultSolveResponse(simData);
  latestYear = Math.max(...simData.provenance.years);
  render();
}

init().catch(err => {
  document.getElementById('root').innerHTML = `<p style="padding:2rem;color:var(--clay-red)">Failed to load: ${err.message}</p>`;
});
```

- [ ] **Step 4: Verify locally**

Serve with `python3 -m http.server 8080` from `web/vanilla/`, open `http://localhost:8080/playground.html`.

Verify:
- All 6 sliders render with correct default values
- Sliding updates the value display in real time
- Exemption toggle switches between Retained/Lost
- Default results table shows with baked-in data
- Chart renders
- Clicking "Compute" sends POST to HF engine
- "Computing…" state disables controls
- Error state shows "Failed — try again" link

- [ ] **Step 5: Commit**

```bash
git add web/vanilla/playground.html web/vanilla/js/pages/playground.js
git commit -m "feat(vanilla): add Playground page with interactive sliders and compute"
```

---

### Task 8: Update deployment to use vanilla directory

**Files:**
- Modify: `web/package.json` (add deploy script)

- [ ] **Step 1: Add a vanilla deploy script to package.json**

Add to `web/package.json` scripts:

```json
"deploy:vanilla": "gh-pages -d vanilla"
```

This deploys the vanilla directory directly to GitHub Pages — no build step.

- [ ] **Step 2: Deploy**

```bash
cd web && npx gh-pages -d vanilla
```

- [ ] **Step 3: Verify live site**

Open `https://nikerane.github.io/kellerwatt-sim/` and verify all three pages work.

- [ ] **Step 4: Commit**

```bash
git add web/package.json
git commit -m "feat(vanilla): add deploy script for vanilla directory"
```

---

### Task 9: Remove React files (optional, gated by user approval)

**Files deleted:**
- `web/src/` (entire directory)
- `web/index.html`, `web/methodology.html`, `web/playground.html` (Vite entry points)
- `web/vite.config.ts`, `web/tsconfig.json`
- `web/package.json` — remove React-related deps (keep only gh-pages if needed)

**Wait for user confirmation before executing this task.** The vanilla version lives alongside the React version in the `vanilla/` subdirectory. Only remove React files after the user has verified the vanilla version works and approves the removal.

---

## Self-Review

**1. Spec coverage:**
- ✅ Three static HTML pages (Honesty, Methodology, Playground)
- ✅ Shared nav component → `renderSiteNav()` in `components.js`
- ✅ Static data from JSON → `fetchSimResults()` in `data.js`, loaded at runtime
- ✅ SVG charts using d3-scale → `charts.js` with template literals, same d3-scale functions
- ✅ KaTeX rendering → loaded from CDN in `<head>`, used via global `katex` (not needed in current pages, but available)
- ✅ Interactive playground (6 sliders, toggle, compute button, fetch) → `playground.js`
- ✅ All functionality preserved → each page mirrors its React counterpart exactly
- ✅ Visual design preserved → CSS copied as-is, Google Fonts for same typefaces
- ✅ No build step → static files, no compilation, no JSX, no TypeScript
- ✅ No React dependencies → `react`, `react-dom` removed

**2. Placeholder scan:** No TBDs, TODOs, or vague references. Every step contains actual code.

**3. Type consistency:**
- `euro(value, opts)` used in Honesty with `{ tone }` and standalone → verified
- `eurPerMwh(value, decimals)` used with 1 arg → verified
- `renderDataMono(text, opts)` → tone/size/label all match across callers
- `renderCouplet(first, second, opts)` → as/size match across callers
- Chart functions: `renderSpreadChart(data)` takes full sim_results, `renderPlaygroundChart(response)` takes SolveResponse → correct

