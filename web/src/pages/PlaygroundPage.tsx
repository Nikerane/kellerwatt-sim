import { useState, useEffect, useRef, useCallback } from "react";
import { SiteNav } from "../components/SiteNav";
import { Eyebrow } from "../components/Eyebrow";
import { Couplet } from "../components/Couplet";
import { PlaygroundSlider } from "../components/PlaygroundSlider";
import { PlaygroundResults } from "../components/PlaygroundResults";
import { PlaygroundChart } from "../components/PlaygroundChart";
import type { SliderDef } from "../components/PlaygroundSlider";
import type { SolveResponse } from "../data/playground";
import { results as defaultResults } from "../data/load";
import { YEARS } from "../data/load";

// ------- engine URL (HF Space) ----------
const ENGINE_URL = "https://nikerane-kellerwatt-engine.hf.space";

// ------- slider definitions ----------
const SLIDERS: SliderDef[] = [
  {
    key: "capacity_kwh",
    label: "Battery capacity",
    min: 50,
    max: 350,
    step: 50,
    default: 200,
    unit: "kWh",
  },
  {
    key: "power_kw",
    label: "Power rating",
    min: 25,
    max: 250,
    step: 50,
    default: 50,
    unit: "kW",
  },
  {
    key: "rte",
    label: "Round-trip efficiency",
    min: 0.75,
    max: 0.95,
    step: 0.05,
    default: 0.90,
    unit: "%",
    formatValue: (v: number) => `${Math.round(v * 100)}%`,
  },
  {
    key: "assumed_spread",
    label: "Assumed spread",
    min: 20,
    max: 120,
    step: 5,
    default: 80,
    unit: "€/MWh",
  },
  {
    key: "cycles_per_day",
    label: "Daily cycle cap",
    min: 0.5,
    max: 3.0,
    step: 0.5,
    default: 1.5,
    unit: "cyc/day",
  },
  {
    key: "grid_fee",
    label: "Grid energy fee",
    min: 0,
    max: 50,
    step: 5,
    default: 0,
    unit: "€/MWh",
  },
];

type ComputeStatus = "idle" | "computing" | "error";

/** Build default SolveResponse from the baked-in sim_results.json so the page
    shows real numbers before the first compute. */
function defaultSolveResponse(): SolveResponse {
  const bp = defaultResults.assumptions.business_plan;
  const years = defaultResults.provenance.years;

  const ceiling: Record<string, number | null> = {};
  const causalR: Record<string, number | null> = {};
  const ceilingGross: Record<string, number | null> = {};
  const causalGross: Record<string, number | null> = {};
  const ceilingCycles: Record<string, number | null> = {};
  const causalCycles: Record<string, number | null> = {};

  for (const s of defaultResults.strategies) {
    for (const yr of s.years) {
      const key = String(yr.year);
      if (s.id === "lp_ceiling") {
        ceiling[key] = yr.ceiling_eur_mwh;
        ceilingGross[key] = yr.gross_eur;
        ceilingCycles[key] = yr.cycles_ac;
      } else if (s.id === "causal_walkforward") {
        causalR[key] = yr.causal_eur_mwh;
        causalGross[key] = yr.gross_eur;
        causalCycles[key] = yr.cycles_ac;
      }
    }
  }

  const wrap = (
    spread: Record<string, number | null>,
    gross: Record<string, number | null>,
    cyclesAc: Record<string, number | null>,
  ) => {
    const out: Record<
      string,
      { spread_eur_mwh: number | null; gross_eur: number | null; cycles_ac: number | null }
    > = {};
    for (const y of years.map(String)) {
      out[y] = {
        spread_eur_mwh: spread[y] ?? null,
        gross_eur: gross[y] ?? null,
        cycles_ac: cyclesAc[y] ?? null,
      };
    }
    return out;
  };

  return {
    schema_version: defaultResults.schema_version,
    years,
    assumed: {
      spread_eur_mwh: bp.assumed_spread_eur_mwh,
      gross_eur: bp.assumed_gross_eur,
      cycles_per_day: bp.assumed_cycles_per_day,
    },
    ceiling: wrap(ceiling, ceilingGross, ceilingCycles),
    causal_retained: wrap(causalR, causalGross, causalCycles),
    causal_lost: wrap(causalR, causalGross, causalCycles),
  };
}

export function PlaygroundPage() {
  const [values, setValues] = useState<Record<string, number>>(() =>
    Object.fromEntries(SLIDERS.map((s) => [s.key, s.default])),
  );
  const [exemption, setExemption] = useState<"retained" | "lost">("retained");
  const [response, setResponse] = useState<SolveResponse>(defaultSolveResponse);
  const [status, setStatus] = useState<ComputeStatus>("idle");
  const latest = Math.max(...YEARS);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  // ------ compute (manual trigger) ------
  const compute = useCallback(async () => {
    if (!ENGINE_URL) return;
    setStatus("computing");
    try {
      const res = await fetch(`${ENGINE_URL}/solve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
      const data: SolveResponse = await res.json();
      if (mountedRef.current) {
        setResponse(data);
        setStatus("idle");
      }
    } catch {
      if (mountedRef.current) setStatus("error");
    }
  }, [values, exemption]);

  const handleSlider = useCallback(
    (key: string, value: number) => {
      setValues((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const handleExemption = useCallback(
    (exc: "retained" | "lost") => {
      setExemption(exc);
    },
    [],
  );

  const isComputing = status === "computing";

  return (
    <main className="kw-page">
      <SiteNav current="playground" />

      {/* Hero */}
      <section className="kw-section kw-section--hearth">
        <div className="kw-section__inner">
          <div className="kw-fade">
            <Eyebrow ember>Interactive playground</Eyebrow>
          </div>
          <div className="kw-fade kw-fade--2" style={{ marginTop: 28 }}>
            <Couplet
              as="h1"
              size="xl"
              first="Change the assumptions."
              second="Watch the numbers move."
            />
          </div>
          <p className="kw-lead kw-fade kw-fade--3" style={{ marginTop: 28 }}>
            Tweak the sliders, then hit Compute. HiGHS — an open-source
            optimisation solver — finds the best charge/discharge schedule against
            real DE-LU day-ahead prices.
          </p>
        </div>
      </section>

      {/* Sliders panel */}
      <section className="kw-section kw-section--bone kw-section--tight">
        <div className="kw-section__inner">
          <div
            style={{ display: "flex", alignItems: "baseline", gap: 16, marginBottom: 28, flexWrap: "wrap" }}
          >
            <Eyebrow>Parameters</Eyebrow>
            <ComputeButton status={status} onClick={compute} />
          </div>
          <div
            className="kw-sliders-grid"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
              gap: 24,
            }}
          >
            {SLIDERS.map((s) => (
              <PlaygroundSlider
                key={s.key}
                slider={s}
                value={values[s.key]}
                onChange={handleSlider}
                disabled={isComputing}
              />
            ))}
            {/* exemption toggle */}
            <div
              className="kw-toggle"
              style={{ display: "flex", flexDirection: "column", gap: 8 }}
            >
              <span
                style={{
                  fontFamily: "var(--sans)",
                  fontSize: "0.85rem",
                  color: "var(--slate)",
                }}
              >
                §118(6) exemption
              </span>
              <span style={{ display: "flex", gap: 8 }}>
                <button
                  type="button"
                  className={`kw-toggle__btn ${exemption === "retained" ? "kw-toggle__btn--active" : ""}`}
                  onClick={() => handleExemption("retained")}
                  disabled={isComputing}
                >
                  Retained
                </button>
                <button
                  type="button"
                  className={`kw-toggle__btn ${exemption === "lost" ? "kw-toggle__btn--active" : ""}`}
                  onClick={() => handleExemption("lost")}
                  disabled={isComputing}
                >
                  Lost
                </button>
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Results table */}
      <section className="kw-section kw-section--bone">
        <div className="kw-section__inner">
          <Eyebrow ember>Results</Eyebrow>
          <div style={{ overflowX: "auto" }}>
            <PlaygroundResults data={response} year={latest} />
          </div>
        </div>
      </section>

      {/* Chart */}
      <section className="kw-section kw-section--hearth">
        <div className="kw-section__inner">
          <Eyebrow>The spread, by year</Eyebrow>
          <Couplet
            first="The best case is what's possible."
            second="The realistic case is what's likely."
            size="lg"
          />
          <div className="kw-split kw-split--chart" style={{ marginTop: 44 }}>
            <p className="kw-lead">
              The chart shows implied spreads — the price difference the battery
              captures per megawatt-hour discharged. Best-case assumes perfect
              knowledge of tomorrow's prices. Realistic uses only past data.
              Hit Compute after changing the sliders to see the curves shift.
            </p>
            <PlaygroundChart data={response} />
          </div>
        </div>
      </section>

      <section className="kw-section kw-section--bone">
        <div className="kw-section__inner">
          <Eyebrow>How this works</Eyebrow>
          <p className="kw-lead" style={{ marginTop: 18 }}>
            HiGHS — an open-source optimisation solver — reads real DE-LU day-ahead
            prices from Energy-Charts and finds the best possible charge/discharge
            schedule for each day. Best-case assumes perfect knowledge of tomorrow's
            prices. Realistic uses only past data, like a real operator would.
          </p>
          <p className="kw-lead" style={{ marginTop: 14, fontSize: "0.85rem", opacity: 0.7 }}>
            Every solve is live — the engine runs on a Hugging Face Space.
            Results from the Validation page are baked in at build time and
            use the same solver and data.
          </p>
        </div>
      </section>
    </main>
  );
}

function ComputeButton({ status, onClick }: { status: ComputeStatus; onClick: () => void }) {
  const isError = status === "error";

  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
      <button
        type="button"
        className="kw-dispatch-btn kw-dispatch-btn--active"
        onClick={onClick}
        disabled={status === "computing"}
        style={{ fontSize: "0.82rem", fontFamily: "var(--mono)" }}
      >
        {status === "computing" ? "Computing…" : "Compute"}
      </button>
      {isError && (
        <span
          role="status"
          style={{
            fontSize: "0.78rem",
            fontFamily: "var(--mono)",
            color: "var(--clay-red)",
          }}
        >
          Failed —{" "}
          <button
            type="button"
            onClick={onClick}
            style={{
              background: "none",
              border: "none",
              color: "var(--clay-red)",
              cursor: "pointer",
              textDecoration: "underline",
              fontSize: "inherit",
              fontFamily: "inherit",
              padding: 0,
            }}
          >
            try again
          </button>
        </span>
      )}
    </span>
  );
}
