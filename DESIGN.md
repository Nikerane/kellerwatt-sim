---
# KellerWatt — machine-readable brand spec (Stitch DESIGN.md format).
# Open any AI build session with "use DESIGN.md" to inherit the brand with zero drift.
# Authoritative prose: docs/brand/brand-guidelines.md. Token CSS: app-package/assets/colors_and_type.css.
name: KellerWatt
tagline: Power that pays you back.
atmosphere: editorial, warm, calm, considered — a good Sunday newspaper, not a VC deck
color:
  hearth:   "#1F3A34"   # identity; dark-green surfaces; headlines on light
  hearth_ink: "#142621" # pressed/shadow variant
  ember:    "#E89B4F"   # ACCENT/SIGNAL ONLY — one per screen, never a fill
  bone:     "#F5F1EA"   # default warm off-white surface
  paper:    "#FBF8F2"   # cards-on-bone, one step lighter
  slate:    "#2C2E2D"   # primary text on light (never pure black)
  stone:    "#E8E2D7"   # dividers, quiet rails
  dusk:     "#4A3850"   # depth, off-peak, shadows
  clay_red: "#D98A7A"   # NEGATIVE VALUES ONLY (negative prices, shortfall, cost)
  app_surface: "#101D18" # owner-app dark surface
type:
  serif: "Fraunces"          # headlines/hero; weight 500; tracking -0.025em; variable opsz
  sans:  "Inter"             # body, UI, buttons, labels; 400/500/600
  mono:  "JetBrains Mono"    # ALL numbers/tariffs/savings + uppercase eyebrows (+0.22em)
  load:  "self-host via Fontsource — not the Google CDN (GDPR; German brand)"
radius: { card: 18px, scale: [4, 8, 12, 18, 24, 999] }
borders: "hairline 0.5px rgba(44,46,45,0.10); no coloured left-border accents, ever"
shadow: "two-layer (1px rim + soft drop); tiers resting/hover/modal; never dramatic"
motion:
  ease: "cubic-bezier(0.2, 0.7, 0.2, 1.0)"   # warm: slow start, gentle settle
  durations: { state: 120ms, transition: 220ms, entrance: 420ms }
  rules: "fades over slides; NO scroll-jacking; NO parallax on web; idle ±1–2px sine drift"
texture: "hex-cell pattern @6–7% opacity, on Hearth/dark sections ONLY — the only texture we own"
layout: { max_width: 1200px, gutter: 24px, rhythm: "one idea per section; dark(Hearth)/light(Bone) alternation" }
stack: "Vite + React + TypeScript (static); Motion(web)+GSAP/Remotion(film); Radix+Vaul; Lucide; d3+SVG; feTurbulence grain"
---

# KellerWatt DESIGN.md

## Atmosphere

Editorial, not enterprise. Calm — a partner, not a cheerleader. The product makes
electricity feel domestic again. Treat the reader as an adult; let the facts do the work.

## Voice

The signature move is the **contrast couplet** — two short declarative sentences where the
second cuts back at the first:
- "Cheap power exists. Most homes can't reach it."
- "Renting basements. Powering Germany."
- "Not a subsidy. A spread."

Sentence case always (except mono eyebrows, which are UPPERCASE tracked). No exclamation
marks. No "revolutionising." Speak directly ("your building", "you earn rent"). Numbers in
JetBrains Mono, currency before figure: **€9,700** not 9.700€.

## Color

Six tokens + Clay-red, used with restraint. Flat fields only — **no gradients, no invented
colors.** Full-bleed Hearth for hero/dark moments; full-bleed Bone for body. **Ember
discipline: if it appears more than once as a fill on a screen, it is wrong** — it is a
signal (active state, live data, one accent), never decoration. Clay-red is reserved strictly
for negative values. Color-role contract for data: Ember = active/revenue · Clay-red =
cost/negative · Bone = neutral/label · Hearth = surface/divider. Never rainbow a chart.

## Typography

Three families. **Fraunces** (serif, 500) for headlines/hero, tight tracking. **Inter** for
everything functional. **JetBrains Mono** for all numbers and for eyebrows (uppercase,
+0.22em tracked, short — they never wrap). Hierarchy comes from size/weight/case, not color.

## Components

- **Editorial card:** Bone/paper surface, 18px radius, 0.5px hairline border, two-layer soft
  shadow, Fraunces headline. Bespoke — do not use a generic library Card.
- **SoC ring (owner app):** stroke-only Ember arc on an Ember-@12%-opacity track over the dark
  app surface; centered JetBrains-Mono %; a 2s pulsing dot at the arc head; no gradient fill.
- **Day chart:** white/Bone line; Ember elapsed segment + faint upcoming segment + pulsing
  head; translucent buy/sell bands (Ember/Clay-red @~15%). Built from d3-scale + hand-rolled
  SVG — no chart library.
- **Honesty panel:** Bone surface (daylight = honesty); 3 columns Assumed / Simulated / Δ;
  Fraunces-italic headers, Inter labels, Mono values; Δ in Ember (positive) / Clay-red
  (negative); no table borders — vertical rhythm only.
- **Controls (tweaks panel):** Radix Slider/Switch/RadioGroup/Tabs/Input; sheets via Vaul.
  Icons: Lucide (stroke-only — **no filled icons**).
- **Buttons:** 12px radius, sentence case, Hearth fill or ghost (Ember border, never Ember fill).

## Layout & elevation

1200px max, 24px gutters, generous whitespace, one idea per section, dark(Hearth)/light(Bone)
alternation separated by a single hairline (no gradient transitions). Shadows quiet; elevation
is restraint, not drama.

## Motion

Warm easing `cubic-bezier(0.2,0.7,0.2,1.0)`; 120/220/420ms. Fades over slides. No
scroll-jacking, no parallax, no WebGL, no cursor trails. Idle micro-motion only: headlines,
numbers, and the persistent battery object drift ±1–2px on a slow sine — nothing fully static.
Numbers count up once on viewport entry.

## Do

- Use Fraunces aggressively for headlines; Mono for every figure.
- Keep Ember to one signal per screen.
- Alternate Hearth/Bone sections; one idea each.
- Hairline borders; 18px cards; two-layer soft shadows.
- Fade-based, restrained motion.

## Don't

- Don't fill with Ember, or use it more than once per screen.
- Don't use gradients, glassmorphism, filled icons, rainbow charts, or stock photos.
- Don't Title-Case or ALL-CAPS (except mono eyebrows). No exclamation marks.
- Don't scroll-jack or parallax on the web.
- Don't put the hex-cell texture on Bone — Hearth/dark only.
