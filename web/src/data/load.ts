import raw from "./sim_results.json";
import type { SimResults, Strategy, Scenario, YearResult } from "./types";

export const results = raw as unknown as SimResults;

export function strategy(id: Strategy["id"]): Strategy {
  const s = results.strategies.find((x) => x.id === id);
  if (!s) throw new Error(`missing strategy ${id}`);
  return s;
}

export function scenario(id: Scenario["id"]): Scenario {
  const s = results.scenarios.find((x) => x.id === id);
  if (!s) throw new Error(`missing scenario ${id}`);
  return s;
}

export function yearOf(s: Strategy, year: number): YearResult {
  const y = s.years.find((x) => x.year === year);
  if (!y) throw new Error(`strategy ${s.id} missing year ${year}`);
  return y;
}

export const YEARS: number[] = results.provenance.years;

// ---- brand-correct formatters (DESIGN.md: currency before figure, € grouping) --

/** €9,700 — currency before figure, thousands separators, no decimals. */
export function euro(value: number | null, opts: { decimals?: number } = {}): string {
  if (value === null || Number.isNaN(value)) return "—";
  const decimals = opts.decimals ?? 0;
  const n = Math.abs(value).toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return `${value < 0 ? "−" : ""}€${n}`;
}

/** A €/MWh rate: "€68.3" with one decimal by default. */
export function eurPerMwh(value: number | null, decimals = 1): string {
  if (value === null || Number.isNaN(value)) return "—";
  return `€${value.toFixed(decimals)}`;
}

export function cycles(value: number | null): string {
  return value === null ? "—" : value.toFixed(2);
}

/** Provisional / estimate metrics show an em dash with the status, never a fake number. */
export function metricDisplay(value: number | null, fmt: (v: number) => string): string {
  return value === null ? "—" : fmt(value);
}

/** Realistic capture as a share of the best-case gross. */
export function captureOfCeiling(year: number): number | null {
  const ce = yearOf(strategy("lp_ceiling"), year).gross_eur;
  const ca = yearOf(strategy("causal_walkforward"), year).gross_eur;
  if (ce === null || ca === null || ce === 0) return null;
  return ca / ce;
}
