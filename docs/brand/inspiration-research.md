# KellerWatt — Design Inspiration Research

> Synthesis of an 8-source deep-dive (2026-06-04). Each source was mined through the
> KellerWatt brand lens (editorial restraint; Hearth/Ember/Bone; Fraunces/Inter/Mono; the
> three surfaces). Actionable, mapped to **landing / owner app / film** and our primitive stack.

## 0. The convergent insight — author a `DESIGN.md`

Two independent sources (VoltAgent's `awesome-design-md` **and** HeyGen's website-to-video
pipeline) center on the same artifact: a **machine-readable brand spec in markdown**
(Google "Stitch" `DESIGN.md` format — YAML token frontmatter + prose sections + explicit
do/don'ts). Any AI build session (Cursor, Claude Code, Copilot) opened with "use DESIGN.md"
inherits the full brand with **zero drift across the three surfaces**.

→ **Done in this pass:** a KellerWatt-native `DESIGN.md` now lives at the repo root.
Closest public analogues to study/borrow structure from:
- **Claude (Anthropic)** — palette twin (warm canvas + single warm accent + dark product card + slab-serif display): https://github.com/VoltAgent/awesome-design-md/blob/main/design-md/claude/DESIGN.md
- **Sanity** — dark-identity logic for the owner app (near-black surface, mono eyebrows, one accent): https://github.com/VoltAgent/awesome-design-md/blob/main/design-md/sanity/DESIGN.md
- **WIRED** — editorial type rhythm; **Runway** — film/dark-hero grammar; **Starbucks** — dark/light section cadence.

## 1. Components & stack — shadcn/ui: cherry-pick, don't adopt

We already own Radix + our CSS-var tokens, so **do not install shadcn wholesale** (its Tailwind
would fight our token CSS). Instead: copy the component *logic* (the Radix a11y wiring), strip
Tailwind classes, wire to our `--gk-*` vars via a single **`tokens/shadcn-bridge.css`**.

| shadcn component | KellerWatt use | Action |
|---|---|---|
| **Drawer** (wraps Vaul) | owner-app bottom sheet / payout | **copy — high value** (snap points + drag handle pre-wired) |
| Slider · Switch · RadioGroup · Tabs · Input/Label | tweaks panel | copy, strip Tailwind, Ember on active state only |
| Dialog · Tooltip · Sonner (toast) | modals / labels / alerts | copy; Clay-red for error toasts only |
| Card · Separator | — | **skip** (bespoke editorial card; `<hr>` in global CSS) |

**Kill the "generic shadcn" tells:** replace `focus-visible:ring-2 ring-offset-2` with
`outline:1.5px solid var(--gk-ember); outline-offset:2px` (one global rule — biggest single
de-generic-fier); 18px radius not 8px; Fraunces headlines; no default `shadow-sm`; JetBrains
Mono for all data. Docs: https://ui.shadcn.com/docs/theming

## 2. Reference sites (verified) — study, don't copy

**Editorial / calm-tech (Awwwards-recognized):**
- **stripe.dev** — two-color palette carried entirely by type + micro-motion; dark↔light cadence. https://stripe.dev/
- **editorialnew.com** — warmth from rhythm alone in pure B/W; narrow-serif ≈ Fraunces register.
- **lifeworld.wetransfer.com** — constrained palette + one-idea-per-section; quiet microinteractions (benchmark for the film's title transitions).
- **stripesessions.com** — deep purple-black (#221b35) ≈ our Hearth; dark card-grid rhythm.
- **wilderness-international.org** / **sustainability.teamthunderfoot.com** — climate sites that avoid "agency reel in green"; dark-imagery→light-copy alternation.
- **betterenergy.com** — the one verified energy-sector ref; one-metric-per-screen pacing (palette not ours).
- **artlist.io/blog/trend-report-2025** — "annual report as landing page"; yellow used once per screen exactly as we use Ember.

**Dashboard patterns (for the owner app + honesty panel):**
- **SoC ring = stroke-only** (Oleg Frolov, "Battery Charge Widget"): Ember arc on an Ember-@12%-opacity track over #101D18; centered JetBrains-Mono %; 2s pulsing dot at the arc head; dark interior (no gradient fill) so it reads as a *window*. https://dribbble.com/shots/18300143-Battery-Charge-Widget
- **Color-role lock** (Charlotte Zhang IoT case study): Ember = battery-active/revenue · Clay-red = cost/negative · Bone = neutral/label · Hearth = surface/divider. Never rainbow a chart.
- **Honesty panel** = GoodUI #115 comparison mechanics, on a **Bone** surface (daylight = honesty), 3 cols Assumed / Simulated / Δ; Fraunces-italic headers, Inter labels, Mono values, Δ in Ember/Clay-red, no table borders. https://goodui.org/patterns/115/
- **Metric card + 40px single-color sparkline** (no axes); **Fortress-style dense Mono table** for Earnings/Building.

## 3. Motion vocabulary (adopt verbatim)

Restrained refs worth replicating: bohdan.design, temper.studio, 1820productions.com,
nory.ai, zwarttechniek.com, Linear, panton.vitra.com. **All map to our easing
`[0.2,0.7,0.2,1.0]` + 120/220/420ms.**

| token | what | Motion params |
|---|---|---|
| `fadeUp` | default section entry | `initial{opacity:0,y:10}` → `{opacity:1,y:0}`, 0.42s |
| `fadeIn` | images/overlays | opacity only, 0.22s |
| `staggerGroup` | cascade children | `staggerChildren:0.06, delayChildren:0.05` |
| `stateTap` | hover/focus | `whileHover{opacity:0.78,y:-2}`, 0.12s |
| `counterIn` | number count-up on viewport enter | spring/AnimateNumber 0→target, 0.42s |
| `idleDrift` | persistent battery/headline life | `y:[0,1.5,0,-1.5,0]`, `repeat:Infinity, dur:6, easeInOut` |
| `crossFadeSlide` | tab/scene swap | `AnimatePresence mode:"wait"`, opacity, 0.22s |

Trigger entries with Motion `useInView({once:true})` — **no scroll-jack, no Y-parallax, no
WebGL, no cursor trails.** Counters use **`@number-flow/react`** (via 21st.dev). Logo rail =
**MagicUI Marquee** (swap edge-fade gradients to Bone/Hearth, monochrome logos,
`--duration:35s`). Calculator slider = **OriginUI Slider-with-Input**. Install pattern:
`npx shadcn@latest add <21st.dev url>`.

## 4. The film — build with Remotion, not HeyGen

**Verdict: Remotion (React → MP4).** Frame-perfect control of fonts (`loadFont()` blocks
render → no Fraunces substitution), colors, the `feTurbulence` grain+vignette overlay
(`<AbsoluteFill>` over every scene), the camera push (`scale(interpolate(frame,[0,end],[1,1.03]))`),
0.65s cross-fades (`<Sequence>` opacity), and the persistent battery object (one component
threaded through 7 `<Sequence>`s). Same React codebase as the site. https://www.remotion.dev/
- **Skip HeyGen/Hyperframes as a renderer** — it pauses GSAP timelines per-frame (red flag) and the LLM-storyboard layer can't hold editorial precision. Use it only for one thing: `npx hyperframes capture` as a machine audit that our hex/fonts are correctly exported.
- **Fallback:** GSAP timeline → OBS 60fps capture → DaVinci Resolve grade.

**7-scene storyboard skeleton** (battery travels & transforms; couplet voice):

| # | BG | Eyebrow | Couplet headline | Data (Mono) | Battery |
|---|----|---------|------------------|-------------|---------|
| 1 | Hearth | THE GRID | Cheap power exists. Most homes can't reach it. | avg spot €0.04/kWh | empty outline, enters |
| 2 | Bone | YOUR BASEMENT | Four walls and a floor. That's all it takes. | footprint 0.6 m² | placed, solid |
| 3 | Hearth | THE ECONOMICS | Buy at 04:00. Sell at 18:00. Every day. | spread up to €0.28/kWh | charging, ember pulse |
| 4 | Bone | THE HARDWARE | One cell stack. No combustion. No compromise. | 6,000+ cycles · 95% DoD | cross-section |
| 5 | Hearth | THE SOFTWARE | It reads the market. You read the savings. | 48h forecast · <200ms | data-orbit glow |
| 6 | Bone | THE NUMBERS | Not a subsidy. A spread. | yr-1 ROI 18–22% | emits ember coins |
| 7 | Hearth | YOUR KELLER | Power that pays you back. Starting this winter. | pilot slots: limited | full, max bloom, push-in |

## 5. Skip list

- **designrocket.io** — a paid Figma→Lovable course; produces generic gradient SaaS output, wrong stack. **Skip.** (For refs use Awwwards "editorial"+"typography" and Semplice.)
- On every source: avoid WebGL heroes, glassmorphism, gradient fills, rainbow charts, filled icons, autoplaying hero video, scroll-jacking, neon accents-as-fills.

## 6. Consolidated next actions (priority order)

1. **`DESIGN.md` at repo root** (done) — the single brand brief for all future AI sessions.
2. **Port `colors_and_type.css` → `web/src/styles/tokens.css`** + write `tokens/shadcn-bridge.css`; add the global Ember focus-ring + 18px-radius overrides.
3. **Build the SoC ring** (stroke-only, Ember arc, pulsing head) — the app's heartbeat — and the **Bone honesty panel** (3-col Mono table) first; they anchor the brand promise.
4. **Wire the motion vocabulary** (§3) as reusable hooks; add `@number-flow/react` counters + MagicUI marquee.
5. **Bootstrap Remotion** with the grain+vignette overlay + `<BatteryObject>` before scene content.
