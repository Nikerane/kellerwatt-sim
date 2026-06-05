import type { DayDetailResponse, DispatchFile } from "./playground";

/** Grid points used in the precomputed lookup table. */
export const CAPACITY_GRID = [50, 100, 175, 250, 350, 450, 500];
export const POWER_GRID = [25, 50, 100, 150, 200, 250];
export const RTE_GRID = [0.75, 0.80, 0.85, 0.90, 0.95];
export const GRID_FEE_GRID = [0, 10, 20, 30, 50];

/** Round a value to the nearest point in a sorted grid. */
export function nearestGridPoint(value: number, grid: number[]): number {
  let best = grid[0];
  let bestDist = Math.abs(value - best);
  for (let i = 1; i < grid.length; i++) {
    const dist = Math.abs(value - grid[i]);
    if (dist < bestDist) {
      bestDist = dist;
      best = grid[i];
    }
  }
  return best;
}

/**
 * Build the combo key used in DispatchFile.combos.
 * RTE is serialised without trailing zeros: 0.9 not 0.90.
 */
export function buildComboKey(power_kw: number, rte: number, grid_fee: number): string {
  return `${power_kw}_${rte}_${grid_fee}`;
}

/** The fixed dates available in every precomputed combo. */
export const PREBUILT_DATES = [
  { label: "★ Best Day", date: "" },   // date filled from combo
  { label: "▼ Worst Day", date: "" },
  { label: "Mar 21", date: "2025-03-21" },
  { label: "Jun 21", date: "2025-06-21" },
  { label: "Jan 15", date: "2025-01-15" },
];

/**
 * Load a DispatchFile for a given capacity (asynchronous fetch).
 * Returns null if the file doesn't exist (404).
 */
export async function loadDispatchFile(capacityKwh: number): Promise<DispatchFile | null> {
  const rounded = nearestGridPoint(capacityKwh, CAPACITY_GRID);
  const filename = `cap_${String(rounded).padStart(3, "0")}.json`;
  try {
    const res = await fetch(`./data/dispatch/${filename}`);
    if (!res.ok) return null;
    return (await res.json()) as DispatchFile;
  } catch {
    return null;
  }
}

/**
 * Try to resolve a DayDetailResponse from the precomputed lookup file.
 * Returns null if the combo or date is not in the file.
 */
export function resolveFromLookup(
  file: DispatchFile,
  powerKw: number,
  rte: number,
  gridFee: number,
  dateStr: string,
): DayDetailResponse | null {
  const roundedPower = nearestGridPoint(powerKw, POWER_GRID);
  const roundedRte = nearestGridPoint(rte, RTE_GRID);
  const roundedFee = nearestGridPoint(gridFee, GRID_FEE_GRID);
  const key = buildComboKey(roundedPower, roundedRte, roundedFee);

  const combo = file.combos[key];
  if (!combo) return null;

  const dayInfo = file.days[dateStr];
  if (!dayInfo) return null;

  const ceiling = combo.ceiling[dateStr];
  const causal = combo.causal[dateStr];
  if (!ceiling || !causal) return null;

  // Available dates for this combo (best + worst + 3 seasonal, deduplicated).
  const seasonal = ["2025-03-21", "2025-06-21", "2025-01-15"];
  const available = [combo.best_date, combo.worst_date, ...seasonal]
    .filter((d, i, arr) => arr.indexOf(d) === i)
    .filter((d) => combo.ceiling[d]);

  return {
    date: dateStr,
    num_intervals: dayInfo.prices.length,
    dt_h: dayInfo.dt_h,
    prices: dayInfo.prices,
    best_date: combo.best_date,
    worst_date: combo.worst_date,
    available_dates: available,
    ceiling,
    causal,
  };
}
