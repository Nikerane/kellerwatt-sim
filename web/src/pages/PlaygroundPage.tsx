import { useState, useEffect, useRef, useCallback } from "react";
import { SiteNav } from "../components/SiteNav";
import { Eyebrow } from "../components/Eyebrow";
import { Couplet } from "../components/Couplet";
import { PlaygroundSlider } from "../components/PlaygroundSlider";
import { PlaygroundResults } from "../components/PlaygroundResults";
import { PlaygroundChart } from "../components/PlaygroundChart";
import type { SliderDef } from "../components/PlaygroundSlider";
import type { SolveResponse, DayDetailResponse } from "../data/playground";
import { results as defaultResults } from "../data/load";
import { YEARS } from "../data/load";
import { DailyDispatchChart } from "../components/DailyDispatchChart";

// ------- engine URL (HF Space) ----------
// When running locally without the HF backend, leave empty to use baked-in defaults.
const ENGINE_URL = "https://nikerane-kellerwatt-engine.hf.space";

// ------- slider definitions ----------
const SLIDERS: SliderDef[] = [
  {
    key: "capacity_kwh",
    label: "Battery capacity",
    min: 50,
    max: 500,
    step: 25,
    default: 200,
    unit: "kWh",
  },
  {
    key: "power_kw",
    label: "Power rating",
    min: 25,
    max: 250,
    step: 25,
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
    step: 0.25,
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

type EngineStatus = "warming" | "ready" | "solving" | "solved" | "error";

/** Build default SolveResponse from the baked-in sim_results.json so the page
    shows real numbers before the backend wakes up. */
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
  const [engineStatus, setEngineStatus] = useState<EngineStatus>(
    ENGINE_URL ? "warming" : "ready",
  );
  const latest = Math.max(...YEARS);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const healthPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);
  const [dayDetail, setDayDetail] = useState<DayDetailResponse | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [dayLoading, setDayLoading] = useState(false);

  // ------ fetch per-day dispatch detail ------
  const fetchDayDetail = useCallback(
    async (dateStr: string) => {
      if (!ENGINE_URL) return;
      setDayLoading(true);
      try {
        const res = await fetch(`${ENGINE_URL}/day-detail`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            date: dateStr,
            battery: {
              capacity_kwh: values.capacity_kwh,
              power_kw: values.power_kw,
              rte: values.rte,
            },
            grid_fee_eur_mwh: values.grid_fee,
          }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: DayDetailResponse = await res.json();
        if (mountedRef.current) {
          setDayDetail(data);
          setSelectedDate(dateStr);
        }
      } catch {
        /* keep previous detail if fetch fails */
      } finally {
        if (mountedRef.current) setDayLoading(false);
      }
    },
    [values],
  );

  // Auto-fetch the first seasonal date when engine is ready
  useEffect(() => {
    if (engineStatus === "solved" && dayDetail === null && ENGINE_URL) {
      fetchDayDetail("2025-03-21");
    }
  }, [engineStatus, dayDetail, fetchDayDetail]);

  // ------ health-check warm-up on mount ------
  useEffect(() => {
    mountedRef.current = true;
    if (!ENGINE_URL) {
      setEngineStatus("ready");
      return;
    }
    let attempts = 0;
    const poll = () => {
      fetch(`${ENGINE_URL}/health`)
        .then((r) => {
          if (r.ok && mountedRef.current) {
            setEngineStatus("ready");
            if (healthPollRef.current) clearInterval(healthPollRef.current);
          }
        })
        .catch(() => {
          /* still warming */
        });
      attempts++;
      if (attempts > 12) {
        // 60s timeout — engine didn't come up
        if (healthPollRef.current) clearInterval(healthPollRef.current);
        if (mountedRef.current) setEngineStatus("error");
      }
    };
    poll(); // immediate first attempt
    healthPollRef.current = setInterval(poll, 5000);
    return () => {
      mountedRef.current = false;
      if (healthPollRef.current) clearInterval(healthPollRef.current);
    };
  }, []);

  // ------ debounced solve ------
  const solve = useCallback(
    (vals: Record<string, number>, exc: "retained" | "lost") => {
      if (!ENGINE_URL) return;
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(async () => {
        setEngineStatus("solving");
        try {
          const res = await fetch(`${ENGINE_URL}/solve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              battery: {
                capacity_kwh: vals.capacity_kwh,
                power_kw: vals.power_kw,
                rte: vals.rte,
              },
              assumed_spread_eur_mwh: vals.assumed_spread,
              cycles_per_day: vals.cycles_per_day,
              grid_fee_eur_mwh: vals.grid_fee,
              exemption: exc,
            }),
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data: SolveResponse = await res.json();
          if (mountedRef.current) {
            setResponse(data);
            setEngineStatus("solved");
          }
        } catch {
          if (mountedRef.current) setEngineStatus("error");
        }
      }, 500);
    },
    [],
  );

  const handleSlider = useCallback(
    (key: string, value: number) => {
      const next = { ...values, [key]: value };
      setValues(next);
      solve(next, exemption);
    },
    [values, exemption, solve],
  );

  const handleExemption = useCallback(
    (exc: "retained" | "lost") => {
      setExemption(exc);
      solve(values, exc);
    },
    [values, solve],
  );

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
            Every slider change re-runs the Python arbitrage engine live — the same
            solver, the same real DE-LU prices. Results appear in seconds.
          </p>
        </div>
      </section>

      {/* Sliders panel */}
      <section className="kw-section kw-section--bone">
        <div className="kw-section__inner">
          <div
            style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 28 }}
          >
            <Eyebrow>Parameters</Eyebrow>
            <EngineBadge
              status={engineStatus}
              onRetry={() => solve(values, exemption)}
            />
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
                disabled={engineStatus === "solving"}
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
                  disabled={engineStatus === "solving"}
                >
                  Retained
                </button>
                <button
                  type="button"
                  className={`kw-toggle__btn ${exemption === "lost" ? "kw-toggle__btn--active" : ""}`}
                  onClick={() => handleExemption("lost")}
                  disabled={engineStatus === "solving"}
                >
                  Lost
                </button>
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Results */}
      <section className="kw-section kw-section--hearth">
        <div className="kw-section__inner">
          <Eyebrow ember>Results — live solved</Eyebrow>
          <div style={{ overflowX: "auto" }}>
            <PlaygroundResults data={response} year={latest} />
          </div>
          <PlaygroundChart data={response} />
        </div>
      </section>

      {/* Daily Dispatch */}
      <section className="kw-section kw-section--bone">
        <div className="kw-section__inner">
          <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 18 }}>
            <Eyebrow>Daily dispatch</Eyebrow>
            {dayDetail && (
              <span style={{
                fontSize: "0.72rem",
                fontFamily: "var(--mono)",
                color: "#4CAF50",
              }}>
                Live solved ✓
              </span>
            )}
          </div>
          <p className="kw-lead" style={{ marginTop: 0, marginBottom: 22 }}>
            Per-interval charge / discharge on a real price curve.
            Best-case shows what you'd earn with perfect information; realistic
            shows what a real strategy would actually capture.
          </p>

          {/* Day picker — best, worst, seasonal */}
          <div style={{
            display: "flex", gap: 8, marginBottom: 28, flexWrap: "wrap",
            alignItems: "center",
          }}>
            {[
              { label: "★ Best Day", date: dayDetail?.best_date ?? "2025-01-20" },
              { label: "▼ Worst Day", date: dayDetail?.worst_date ?? "2025-10-04" },
              { label: "Mar 21", date: "2025-03-21" },
              { label: "Jun 21", date: "2025-06-21" },
              { label: "Jan 15", date: "2025-01-15" },
            ].map(({ label, date }) => (
              <button
                key={date}
                type="button"
                className={`kw-dispatch-btn${date === selectedDate ? " kw-dispatch-btn--active" : ""}`}
                disabled={dayLoading}
                onClick={() => fetchDayDetail(date)}
              >
                {label}
              </button>
            ))}
            {dayLoading && (
              <span style={{ fontSize: "0.78rem", opacity: 0.5, fontFamily: "var(--mono)" }}>
                Loading…
              </span>
            )}
          </div>

          {dayDetail && (
            <div
              className="kw-dispatch-grid"
              style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}
            >
              <DailyDispatchChart data={dayDetail} strategy="ceiling" />
              <DailyDispatchChart data={dayDetail} strategy="causal" />
            </div>
          )}
          {!dayDetail && (
            <p style={{ fontSize: "0.88rem", opacity: 0.6 }}>
              Adjust sliders to see daily dispatch charts.
            </p>
          )}
        </div>
      </section>

      <footer className="kw-footer">
        <Eyebrow>Engine</Eyebrow>
        <p style={{ marginTop: 14 }}>
          Same Python solver (HiGHS {defaultResults.solver.version}) on real DE-LU
          day-ahead prices from Energy-Charts. Best-case is a perfect-information
          upper bound. Realistic is a backtested estimate. IRR / payback stay null
          until diligence items land.
        </p>
      </footer>
    </main>
  );
}

function EngineBadge({
  status,
  onRetry,
}: {
  status: EngineStatus;
  onRetry: () => void;
}) {
  const config: Record<
    EngineStatus,
    { text: string; dot: string }
  > = {
    warming: { text: "Warming up…", dot: "var(--ember)" },
    ready: { text: "Ready ✓", dot: "#4CAF50" },
    solving: { text: "Solving…", dot: "var(--ember)" },
    solved: { text: "Solved ✓", dot: "#4CAF50" },
    error: { text: "Unreachable", dot: "var(--clay-red)" },
  };
  const c = config[status];
  const isError = status === "error";

  return (
    <span
      role="status"
      aria-live="polite"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontSize: "0.78rem",
        fontFamily: "var(--mono)",
        color: c.dot,
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          backgroundColor: c.dot,
          animation:
            status === "warming" || status === "solving"
              ? "kw-pulse 1.4s ease-in-out infinite"
              : undefined,
        }}
      />
      {c.text}
      {isError && (
        <button
          type="button"
          onClick={onRetry}
          style={{
            marginLeft: 6,
            background: "none",
            border: "1px solid var(--clay-red)",
            color: "var(--clay-red)",
            borderRadius: 4,
            cursor: "pointer",
            fontSize: "0.72rem",
            padding: "1px 6px",
          }}
        >
          Retry
        </button>
      )}
    </span>
  );
}
