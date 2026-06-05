import { describe, it, expect } from "vitest";
import {
  euro,
  eurPerMwh,
  cycles,
  captureOfCeiling,
  strategy,
  scenario,
  yearOf,
  results,
  YEARS,
} from "./load";

describe("formatters (DESIGN.md: currency before figure)", () => {
  it("formats euros with the symbol first and thousands separators", () => {
    expect(euro(9947)).toBe("€9,947");
    expect(euro(7030)).toBe("€7,030");
  });
  it("uses a real minus sign for negatives (cost/negative)", () => {
    expect(euro(-100)).toBe("−€100");
  });
  it("renders an em dash for missing values, never a fake zero", () => {
    expect(euro(null)).toBe("—");
    expect(eurPerMwh(null)).toBe("—");
    expect(cycles(null)).toBe("—");
  });
  it("formats €/MWh rates to one decimal", () => {
    expect(eurPerMwh(68.3)).toBe("€68.3");
    expect(eurPerMwh(77.3)).toBe("€77.3");
  });
});

describe("data accessors", () => {
  it("exposes both strategies with the right status", () => {
    expect(strategy("lp_ceiling").status).toBe("validated");
    expect(strategy("causal_walkforward").status).toBe("estimate");
  });
  it("locks the validated ceilings on the wire", () => {
    const ceil = strategy("lp_ceiling");
    expect(yearOf(ceil, 2023).ceiling_eur_mwh).toBe(61.1);
    expect(yearOf(ceil, 2024).ceiling_eur_mwh).toBe(68.3);
    expect(yearOf(ceil, 2025).ceiling_eur_mwh).toBe(77.3);
  });
  it("keeps scenario IRR/payback provisional and blank", () => {
    for (const id of ["causal_exemption_retained", "causal_exemption_lost"] as const) {
      const s = scenario(id);
      expect(s.irr.status).toBe("provisional");
      expect(s.irr.value).toBeNull();
      expect(s.payback_years.value).toBeNull();
    }
  });
  it("reconciles the assumed case to the identity, not the deck's 9947", () => {
    expect(results.assumptions.business_plan.assumed_gross_eur).toBeCloseTo(7884, 0);
  });
});

describe("captureOfCeiling", () => {
  it("is a sane fraction below 1 for every year", () => {
    for (const y of YEARS) {
      const c = captureOfCeiling(y);
      expect(c).not.toBeNull();
      expect(c!).toBeGreaterThan(0.2);
      expect(c!).toBeLessThan(1);
    }
  });
});
