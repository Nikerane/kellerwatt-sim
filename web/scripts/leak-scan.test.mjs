import { describe, it, expect } from "vitest";
import { findLeaks, checkSanitizedDoc, FORBIDDEN } from "./leak-scan.mjs";
import data from "../src/data/sim_results.json";

describe("B6 sanitized leak scan", () => {
  it("flags confidential markers in arbitrary text", () => {
    expect(findLeaks('{"capex_eur":123456}')).toContain("capex_eur");
    expect(findLeaks("loaded from dist/real/sim_results.json")).toContain("dist/real");
    expect(findLeaks('{"ceiling_eur_mwh":77.3}')).toEqual([]); // ceilings are public
  });

  it("the actual sanitized data module is clean", () => {
    expect(findLeaks(JSON.stringify(data), FORBIDDEN)).toEqual([]);
    expect(checkSanitizedDoc(data)).toEqual([]);
  });

  it("catches a real IRR leaking into the public bundle", () => {
    const bad = {
      scenarios: [{ id: "x", irr: { value: 0.12 }, payback_years: { value: null } }],
    };
    expect(checkSanitizedDoc(bad).length).toBeGreaterThan(0);
  });
});
