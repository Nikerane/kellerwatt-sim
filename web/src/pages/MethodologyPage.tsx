import { SiteNav } from "../components/SiteNav";
import { Eyebrow } from "../components/Eyebrow";
import { Couplet } from "../components/Couplet";
import { DataMono } from "../components/DataMono";
import { results, YEARS, strategy } from "../data/load";

export function MethodologyPage() {
  const bp = results.assumptions.business_plan;
  const battery = results.assumptions.battery;
  const latest = Math.max(...YEARS);
  const ceilStrat = strategy("lp_ceiling");

  // Derive the identity: spread × usable MWh × cycles × days = annual gross
  const cyclesPerDay = bp.assumed_cycles_per_day;
  const days = 365;
  const usable = battery.usable_kwh;
  const mwhPerYear = (usable * cyclesPerDay * days) / 1000;
  const implied = bp.assumed_gross_eur / mwhPerYear;

  return (
    <main className="kw-page">
      <SiteNav current="methodology" />

      {/* Hero */}
      <section className="kw-section kw-section--hearth">
        <div className="kw-section__inner">
          <Eyebrow ember>How the number is computed</Eyebrow>
          <Couplet
            as="h1"
            size="lg"
            first="The conclusions are on the Validation page."
            second="Here are the workings."
          />
        </div>
      </section>

      {/* Assumptions */}
      <section className="kw-section kw-section--bone">
        <div className="kw-section__inner">
          <Eyebrow>Assumptions</Eyebrow>
          <p className="kw-lead" style={{ marginTop: 18, marginBottom: 24 }}>
            Every figure on the Validation page starts from a single battery unit
            and a set of fixed inputs — the same spreadsheet model, solved against
            real DE-LU prices.
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 20, marginBottom: 36 }}>
            <StatCard label="Battery capacity" value="200 kWh" />
            <StatCard label="Power rating" value="50 kW" />
            <StatCard label="Round-trip efficiency" value="90%" />
            <StatCard label="Usable energy" value={`${usable} kWh`} />
            <StatCard label="Cycles per day (assumed)" value={cyclesPerDay.toFixed(2)} />
            <StatCard label="Operating days" value="365" />
            <StatCard label="Assumed spread" value={`€${bp.assumed_spread_eur_mwh}/MWh`} />
            <StatCard label="Solver" value={`${results.solver.name} ${results.solver.version}`} />
          </div>
        </div>
      </section>

      {/* Revenue identity */}
      <section className="kw-section kw-section--bone kw-section--tight">
        <div className="kw-section__inner">
          <Eyebrow>Revenue identity</Eyebrow>
          <p className="kw-lead" style={{ marginTop: 18, marginBottom: 24 }}>
            The assumed case is a simple multiplication — not a market simulation.
            The formula is:
          </p>

          <div style={{
            fontFamily: "var(--mono)", fontSize: "0.95rem",
            background: "var(--paper)", padding: "20px 24px",
            borderRadius: "var(--r-12)", border: "var(--hairline)",
            lineHeight: 1.7,
          }}>
            <div>
              gross = spread × usable_kWh × cycles_per_day × days ÷ 1000
            </div>
            <div style={{ marginTop: 8, opacity: 0.6 }}>
              = {bp.assumed_spread_eur_mwh} × {usable} × {cyclesPerDay} × {days} ÷ 1000
            </div>
            <div style={{ marginTop: 4 }}>
              = <DataMono tone="ember" size="lg">{Math.round(bp.assumed_gross_eur).toLocaleString()}</DataMono> gross per year
            </div>
          </div>

          <p className="kw-lead" style={{ marginTop: 20, opacity: 0.7, fontSize: "0.92rem" }}>
            The implied spread works backwards from the deck's claimed €9,947 —
            but that figure requires <DataMono tone="muted">€{(9947 / (usable * cyclesPerDay * days / 1000)).toFixed(1)}/MWh</DataMono>,
            not €80. The <DataMono tone="ember">€{bp.assumed_spread_eur_mwh}</DataMono> assumed
            spread yields <DataMono tone="ember">€{Math.round(bp.assumed_gross_eur).toLocaleString()}</DataMono>.
          </p>
        </div>
      </section>

      {/* How the real numbers are computed */}
      <section className="kw-section kw-section--bone kw-section--tight">
        <div className="kw-section__inner">
          <Eyebrow>How the real numbers are computed</Eyebrow>
          <p className="kw-lead" style={{ marginTop: 18, marginBottom: 24 }}>
            The validated best-case and realistic figures come from running a
            mixed-integer linear program (MILP) on real Energy-Charts day-ahead
            prices across {YEARS.length} years.
          </p>

          <div style={{ display: "grid", gap: 16 }}>
            <MethodStep
              num="1"
              title="Load real prices"
              body={`For each day from ${YEARS[0]} to ${latest}, fetch DE-LU day-ahead hourly prices from Energy-Charts.info. These are the actual market-clearing prices — not forecasts.`}
            />
            <MethodStep
              num="2"
              title="Solve the ceiling LP"
              body={`For each day, a linear program finds the profit-maximising charge-discharge schedule with perfect knowledge of the next 24 hours of prices. This is the upper bound — no real operator can achieve this, but it's a validated benchmark. The solver is HiGHS, an open-source MILP solver.`}
            />
            <MethodStep
              num="3"
              title="Run the causal walk-forward"
              body={`A realistic strategy that decides charge/discharge with a 28-day trailing threshold — it sees only past prices, not future ones. This produces the backtested estimate.`}
            />
            <MethodStep
              num="4"
              title="Compute implied spreads"
              body={`Annual gross € ÷ MWh discharged = implied spread in €/MWh. This is the single number that makes the cases comparable — the same "price difference captured per unit of energy" regardless of battery size or cycle count.`}
            />
          </div>
        </div>
      </section>

      {/* Limitations */}
      <section className="kw-section kw-section--bone kw-section--tight">
        <div className="kw-section__inner">
          <Eyebrow>Limitations</Eyebrow>
          <ul className="kw-diligence__list" style={{ marginTop: 18 }}>
            <DiligenceItem body="Prices are day-ahead only. Intraday and balancing-market revenues are not included." />
            <DiligenceItem body="Battery degradation is modelled as a fixed 2%/yr capacity loss per the assumptions spreadsheet." />
            <DiligenceItem body="The causal strategy uses a 28-day trailing threshold. Real operators use more sophisticated forecasting." />
            <DiligenceItem body="Grid fees use the simplified Energy-Charts model. Real German grid fees vary by region and voltage level." />
            <DiligenceItem body="Ancillary-service revenue (FCR, aFRR) is excluded — arbitrage only." />
            <DiligenceItem body="The model assumes one full cycle per day. Multi-cycle strategies may capture more value." />
          </ul>
        </div>
      </section>

      <footer className="kw-footer">
        <Eyebrow>Provenance</Eyebrow>
        <p style={{ marginTop: 14 }}>
          {results.provenance.data_source} · {results.provenance.price_zone} ·
          {" "}{results.provenance.years.join("–")} · schema v{results.schema_version}
        </p>
      </footer>
    </main>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div style={{
      background: "var(--paper)", padding: "16px 18px",
      borderRadius: "var(--r-12)", border: "var(--hairline)",
    }}>
      <div style={{ fontSize: "0.72rem", opacity: 0.5, fontFamily: "var(--mono)", marginBottom: 4 }}>
        {label}
      </div>
      <DataMono size="md">{value}</DataMono>
    </div>
  );
}

function MethodStep({ num, title, body }: { num: string; title: string; body: string }) {
  return (
    <div style={{ display: "flex", gap: 16, alignItems: "baseline" }}>
      <span style={{
        flex: "0 0 auto", width: 28, height: 28,
        borderRadius: "50%", background: "var(--hearth)",
        color: "var(--bone)", display: "flex", alignItems: "center",
        justifyContent: "center", fontSize: "0.78rem",
        fontFamily: "var(--mono)", fontWeight: 500,
      }}>
        {num}
      </span>
      <div>
        <strong style={{ fontFamily: "var(--serif)", fontWeight: 500, fontSize: "1.05rem" }}>
          {title}
        </strong>
        <p style={{ margin: "4px 0 0", opacity: 0.72, fontSize: "0.92rem", lineHeight: 1.55 }}>
          {body}
        </p>
      </div>
    </div>
  );
}

function DiligenceItem({ body }: { body: string }) {
  return (
    <li className="kw-diligence__item" style={{ borderBottom: "none", paddingBottom: 8 }}>
      <span style={{ opacity: 0.72, fontSize: "0.92rem" }}>{body}</span>
    </li>
  );
}
