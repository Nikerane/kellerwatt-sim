import { describe, it, expect, vi } from "vitest";
import {
  nearestGridPoint,
  buildComboKey,
  resolveFromLookup,
  CAPACITY_GRID,
  POWER_GRID,
  RTE_GRID,
  GRID_FEE_GRID,
  loadDispatchFile,
} from "./dispatchLookup";
import type { DispatchFile } from "./playground";

describe("nearestGridPoint", () => {
  it("returns exact match", () => {
    expect(nearestGridPoint(250, CAPACITY_GRID)).toBe(250);
  });

  it("rounds up to nearest", () => {
    expect(nearestGridPoint(205, CAPACITY_GRID)).toBe(175);
    expect(nearestGridPoint(290, CAPACITY_GRID)).toBe(250);
  });

  it("rounds down to nearest", () => {
    expect(nearestGridPoint(230, CAPACITY_GRID)).toBe(250);
  });

  it("clamps to first", () => {
    expect(nearestGridPoint(10, CAPACITY_GRID)).toBe(50);
  });

  it("clamps to last", () => {
    expect(nearestGridPoint(999, CAPACITY_GRID)).toBe(500);
  });

  it("works for power grid", () => {
    expect(nearestGridPoint(55, POWER_GRID)).toBe(50);
    expect(nearestGridPoint(80, POWER_GRID)).toBe(100);
  });

  it("works for RTE grid", () => {
    expect(nearestGridPoint(0.87, RTE_GRID)).toBe(0.85);
    expect(nearestGridPoint(0.88, RTE_GRID)).toBe(0.90);
  });

  it("works for grid fee grid", () => {
    expect(nearestGridPoint(7, GRID_FEE_GRID)).toBe(10);
    expect(nearestGridPoint(3, GRID_FEE_GRID)).toBe(0);
  });
});

describe("buildComboKey", () => {
  it("builds correct key format", () => {
    expect(buildComboKey(50, 0.90, 0)).toBe("50_0.9_0");
    expect(buildComboKey(100, 0.75, 20)).toBe("100_0.75_20");
    expect(buildComboKey(250, 0.95, 50)).toBe("250_0.95_50");
  });
});

describe("resolveFromLookup", () => {
  const mockFile: DispatchFile = {
    capacity_kwh: 200,
    days: {
      "2025-01-20": { prices: [91.9, 88.9, 87.2], dt_h: 1.0 },
      "2025-10-04": { prices: [50.0, 45.0, 40.0], dt_h: 1.0 },
      "2025-03-21": { prices: [60.0, 55.0, 50.0], dt_h: 1.0 },
      "2025-06-21": { prices: [30.0, 35.0, 40.0], dt_h: 1.0 },
      "2025-01-15": { prices: [70.0, 65.0, 60.0], dt_h: 1.0 },
    },
    combos: {
      "50_0.9_0": {
        best_date: "2025-01-20",
        worst_date: "2025-10-04",
        ceiling: {
          "2025-01-20": {
            gross_eur: 21.82, mwh_discharged: 0.171, mwh_charged: 0.19,
            avg_buy_price: 20.5, avg_sell_price: 123.8,
            charge_kw: [0, 50, 50], discharge_kw: [0, 0, 50], soc_kwh: [20, 63, 20],
          },
          "2025-03-21": {
            gross_eur: 10.0, mwh_discharged: 0.1, mwh_charged: 0.11,
            avg_buy_price: 30.0, avg_sell_price: 80.0,
            charge_kw: [0, 0, 0], discharge_kw: [0, 0, 0], soc_kwh: [20, 20, 20],
          },
          "2025-06-21": {
            gross_eur: 12.0, mwh_discharged: 0.08, mwh_charged: 0.09,
            avg_buy_price: 25.0, avg_sell_price: 90.0,
            charge_kw: [0, 0, 0], discharge_kw: [0, 0, 0], soc_kwh: [20, 20, 20],
          },
          "2025-01-15": {
            gross_eur: 18.0, mwh_discharged: 0.12, mwh_charged: 0.13,
            avg_buy_price: 35.0, avg_sell_price: 110.0,
            charge_kw: [0, 0, 0], discharge_kw: [0, 0, 0], soc_kwh: [20, 20, 20],
          },
          "2025-10-04": {
            gross_eur: 5.0, mwh_discharged: 0.05, mwh_charged: 0.06,
            avg_buy_price: 40.0, avg_sell_price: 80.0,
            charge_kw: [0, 0, 0], discharge_kw: [0, 0, 0], soc_kwh: [20, 20, 20],
          },
        },
        causal: {
          "2025-01-20": {
            gross_eur: 15.84, mwh_discharged: 0.171, mwh_charged: 0.19,
            avg_buy_price: 15.7, avg_sell_price: 110.2,
            charge_kw: [0, 50, 39], discharge_kw: [0, 0, 0], soc_kwh: [20, 63, 100],
          },
          "2025-03-21": {
            gross_eur: 8.0, mwh_discharged: 0.1, mwh_charged: 0.11,
            avg_buy_price: 25.0, avg_sell_price: 75.0,
            charge_kw: [0, 0, 0], discharge_kw: [0, 0, 0], soc_kwh: [20, 20, 20],
          },
          "2025-06-21": {
            gross_eur: 9.0, mwh_discharged: 0.08, mwh_charged: 0.09,
            avg_buy_price: 22.0, avg_sell_price: 85.0,
            charge_kw: [0, 0, 0], discharge_kw: [0, 0, 0], soc_kwh: [20, 20, 20],
          },
          "2025-01-15": {
            gross_eur: 14.0, mwh_discharged: 0.12, mwh_charged: 0.13,
            avg_buy_price: 32.0, avg_sell_price: 105.0,
            charge_kw: [0, 0, 0], discharge_kw: [0, 0, 0], soc_kwh: [20, 20, 20],
          },
          "2025-10-04": {
            gross_eur: 3.0, mwh_discharged: 0.05, mwh_charged: 0.06,
            avg_buy_price: 38.0, avg_sell_price: 78.0,
            charge_kw: [0, 0, 0], discharge_kw: [0, 0, 0], soc_kwh: [20, 20, 20],
          },
        },
      },
    },
  };

  it("returns a DayDetailResponse for a known combo + date", () => {
    const result = resolveFromLookup(mockFile, 50, 0.90, 0, "2025-01-20");
    expect(result).not.toBeNull();
    expect(result!.date).toBe("2025-01-20");
    expect(result!.num_intervals).toBe(3);
    expect(result!.prices).toEqual([91.9, 88.9, 87.2]);
    expect(result!.ceiling.gross_eur).toBe(21.82);
    expect(result!.causal.gross_eur).toBe(15.84);
    expect(result!.best_date).toBe("2025-01-20");
    expect(result!.worst_date).toBe("2025-10-04");
  });

  it("rounds slider values to nearest grid point", () => {
    const result = resolveFromLookup(mockFile, 55, 0.88, 3, "2025-01-20");
    expect(result).not.toBeNull();
  });

  it("returns null for missing combo", () => {
    const result = resolveFromLookup(mockFile, 25, 0.90, 0, "2025-01-20");
    expect(result).toBeNull();
  });

  it("returns null for missing date", () => {
    const result = resolveFromLookup(mockFile, 50, 0.90, 0, "2025-12-25");
    expect(result).toBeNull();
  });

  it("available_dates includes best, worst, and seasonal", () => {
    const result = resolveFromLookup(mockFile, 50, 0.90, 0, "2025-01-20");
    expect(result!.available_dates).toContain("2025-01-20");
    expect(result!.available_dates).toContain("2025-10-04");
    expect(result!.available_dates).toContain("2025-03-21");
    expect(result!.available_dates).toContain("2025-06-21");
    expect(result!.available_dates).toContain("2025-01-15");
  });
});

describe("loadDispatchFile", () => {
  it("fetches the correct file for a capacity", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ capacity_kwh: 250, days: {}, combos: {} }),
    });
    globalThis.fetch = mockFetch as any;

    const result = await loadDispatchFile(250);
    expect(result).not.toBeNull();
    expect(result!.capacity_kwh).toBe(250);
    expect(mockFetch).toHaveBeenCalledWith("./data/dispatch/cap_250.json");
  });

  it("returns null on 404", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: false });
    globalThis.fetch = mockFetch as any;

    const result = await loadDispatchFile(50);
    expect(result).toBeNull();
  });

  it("rounds to nearest capacity before fetching", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ capacity_kwh: 175, days: {}, combos: {} }),
    });
    globalThis.fetch = mockFetch as any;

    await loadDispatchFile(190);
    expect(mockFetch).toHaveBeenCalledWith("./data/dispatch/cap_175.json");
  });
});
