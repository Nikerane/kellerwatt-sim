# KellerWatt — Design & Brand Philosophy

> **Status:** canonical. This file governs every visual/verbal decision across the landing
> page, the film, and the owner app. When in doubt, this document wins.

## The idea in one sentence

**Editorial, not enterprise.** A warm, quiet, considered brand that treats the reader as an
adult and lets the facts do the work. Think a good Sunday newspaper, not a VC pitch deck.

## The one-line brief

Warm, grounded, editorial. The brand is calm — a partner, not a cheerleader. The product
makes electricity feel domestic again.

---

## Voice

The signature move: the **contrast couplet** — two short declarative sentences where the
second cuts back at the first.

- "Cheap power exists. Most homes can't reach it."
- "Renting basements. Powering Germany."
- "Power is cheap when no one needs it. Costly when everyone does."

**Rules**
- Sentence case always. Never Title Case, never ALL CAPS except mono eyebrows.
- Short, factual, confident. No exclamation marks. No "revolutionising."
- Speak directly ("your building", "you earn rent") but never like a cheerleader.
- Numbers always in JetBrains Mono. Currency before figure: **€9,700** not 9.700€.

---

## Color — six tokens, used with restraint

| Token | Hex | Role |
|---|---|---|
| Hearth | `#1F3A34` | Identity. Dark-green backgrounds, headlines on light. |
| Ember | `#E89B4F` | Signal only. Active states, live data, one accent per screen. Never fill. |
| Bone | `#F5F1EA` | Default page surface. Warm off-white with paper feel. |
| Slate | `#2C2E2D` | Primary text on light. Almost-black, never pure. |
| Stone | `#E8E2D7` | Dividers, quiet rails. |
| Dusk | `#4A3850` | Depth. Off-peak, shadows. |
| Clay red | `#D98A7A` | Negative values only (negative prices, shortfall). |

- No gradients. No invented colors. Backgrounds are flat fields — full-bleed **Hearth** for
  hero/dark moments, full-bleed **Bone** for body.
- **Ember discipline:** if it appears more than once as a fill on any screen, it's being used
  wrong.

---

## Typography — a three-family system

| Family | Weight | Use |
|---|---|---|
| Fraunces (serif) | 500 | Headlines, hero statements. Tight tracking (−0.025em). |
| Inter (sans) | 400/500/600 | Body, UI, buttons, labels. Everything functional. |
| JetBrains Mono | 400/500 | Numbers, tariffs, savings, ALL CAPS eyebrows (+0.22em tracked). |

Eyebrows (section labels) are always mono, uppercase, tracked, short. **They never wrap.**

---

## Visual texture — one rule

The **hex-cell pattern** (faint hexagons at 6–7% opacity over Hearth) is the only texture the
brand owns. Used sparingly on dark sections and the film. **Never on bone backgrounds.**

- No photography invented from scratch.
- No decorative SVG illustrations.
- No icons with fills.

---

## Layout

- Page max-width: **1200px**, 24px gutters.
- One idea per section — generous breathing room, never crowded.
- Hairline borders (**0.5px**, `rgba(44,46,45,0.10)`) — almost imperceptible.
- No coloured left-border accents on cards. Ever.
- Shadows: two-layer (1px rim + soft drop). Three tiers: resting / hover / modal.
- Corner radii: 4 / 8 / 12 / 18 / 24 / 999px. **18px is the canonical card.**
- Buttons: 12px radius, sentence case, Hearth fill or ghost border.

---

## Motion

- Default easing: `cubic-bezier(0.2, 0.7, 0.2, 1.0)` — slow start, warm gentle settle.
- Durations: **120ms** (state), **220ms** (transition), **420ms** (entrance).
- Fades preferred over slides. No parallax on the web. No scroll-jacking.
- **Film:** mild camera push (1.0→1.03×), hex texture drifts slower than foreground
  (parallax), vignette + grain overlay + breathing ember bloom on every scene.
- **Idle micro-motion:** landed headlines and numbers drift ±1–2px on a slow sine — nothing
  fully static.

---

## Applied across the three deliverables

**Landing page** — Alternates dark (Hearth) and light (Bone) sections. Hero uses the real
apartment photo with a warm Hearth scrim. Data in JetBrains Mono with sourced citations.
Cards on paper (`#FBF8F2`) one step lighter than Bone.

**Film** — 7 scenes alternating dark/light, each ~8–9s. Every scene has one eyebrow, one
headline, and supporting data. The battery is a single persistent visual object that travels
through the whole film. Cross-fades at 0.65s. Grain + vignette as a top-level overlay
unifying every scene.

**Owner App** — Dark surface (`#101D18`), Ember as live-state accent, all data in JetBrains
Mono. SoC ring, directional flow arrows, charge/discharge synced to buy/sell label. Tweaks
panel exposes trading strategy, day speed, lease, building name.

---

## Implementation foundation (reference)

A production token system that implements this philosophy already exists at
`repos/app-package/assets/colors_and_type.css` (CSS custom properties: palette, type scale,
radii, shadows, motion easings) plus reusable visual atoms in `repos/app-package/kwapp-sim.jsx`
(`Ring`, `DayChart`, `Bars`, `Card`, `Eyebrow`, `Dot`). Treat that token file as the
canonical foundation to adopt — not as one-off inspiration. See
`docs/superpowers/specs/2026-06-04-kellerwatt-arbitrage-sim-design.md` for how the rigorous
Python simulation feeds real numbers into these surfaces.
