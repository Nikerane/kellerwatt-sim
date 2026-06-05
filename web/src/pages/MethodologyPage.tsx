import { SiteNav } from "../components/SiteNav";
import { Eyebrow } from "../components/Eyebrow";
import { Couplet } from "../components/Couplet";
import { DataMono } from "../components/DataMono";
import { results, YEARS } from "../data/load";

export function MethodologyPage() {
  const bp = results.assumptions.business_plan;
  const battery = results.assumptions.battery;
  const latest = Math.max(...YEARS);
  const cyclesPerDay = bp.assumed_cycles_per_day;
  const usable = battery.usable_kwh;
  // Capture % for latest year: realistic gross / best-case gross
  const ceilLatest = results.strategies.find(s => s.id === "lp_ceiling")!.years.find(y => y.year === latest)!;
  const causLatest = results.strategies.find(s => s.id === "causal_walkforward")!.years.find(y => y.year === latest)!;
  const capturePct = Math.round((causLatest.gross_eur! / ceilLatest.gross_eur!) * 100);

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
            real German day-ahead prices.
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

      {/* How the real numbers are computed */}
      <section className="kw-section kw-section--bone kw-section--tight">
        <div className="kw-section__inner">
          <Eyebrow>How the real numbers are computed</Eyebrow>
          <p className="kw-lead" style={{ marginTop: 18, marginBottom: 24 }}>
            The validated best-case and realistic figures come from running{" "}
            <strong>HiGHS</strong> — a free, industry-standard solver —
            on real Energy-Charts day-ahead prices across {YEARS.length} years
            ({YEARS[0]} to {latest}). Both strategies use the exact same data
            — ~26,000 hourly prices over 1,095 days. The difference is what they
            are allowed to know.
          </p>

          {/* Best-case */}
          <div style={{
            background: "var(--paper)", padding: "20px 24px",
            borderRadius: "var(--r-12)", border: "var(--hairline)",
            marginBottom: 20,
          }}>
            <strong style={{ fontFamily: "var(--serif)", fontWeight: 500, fontSize: "1.1rem" }}>
              1. Best case — perfect foresight
            </strong>
            <p style={{ marginTop: 10, opacity: 0.75, lineHeight: 1.6 }}>
              The solver gets all 24 hourly prices for a day and finds the
              charge-and-sell schedule that earns the most. It buys when power is
              cheap and sells when it's dear —{" "}
              <strong>because it already knows every price for that day.</strong>
            </p>
            <p style={{ marginTop: 8, opacity: 0.6, fontSize: "0.9rem" }}>
              This is a <strong>ceiling</strong>. No real operator can reach it —
              nobody knows the next hour's price. But it's a useful benchmark: the
              real result can never beat it. Every figure is checked to the cent on
              real prices, not a forecast.
            </p>
          </div>

          {/* Realistic */}
          <div style={{
            background: "var(--paper)", padding: "20px 24px",
            borderRadius: "var(--r-12)", border: "var(--hairline)",
            marginBottom: 20,
          }}>
            <strong style={{ fontFamily: "var(--serif)", fontWeight: 500, fontSize: "1.1rem" }}>
              2. Realistic — blind to the future
            </strong>
            <p style={{ marginTop: 10, opacity: 0.75, lineHeight: 1.6 }}>
              This strategy runs <strong>blind to the future.</strong> At each hour
              it knows only the price right now and the prices of the past 28 days.
              The rule is simple: if power is currently cheap against those 28 days,
              buy; if it's dear, sell. No foresight — the same information a real
              operator has.
            </p>
            <p style={{ marginTop: 8, opacity: 0.6, fontSize: "0.9rem" }}>
              This is a <strong>backtested estimate</strong> — what a real operator
              following a simple rule could have earned. It captures about{" "}
              {capturePct}% of the best case in {latest}.
            </p>
          </div>

          {/* Summarising step */}
          <div style={{
            background: "var(--paper)", padding: "20px 24px",
            borderRadius: "var(--r-12)", border: "var(--hairline)",
          }}>
            <strong style={{ fontFamily: "var(--serif)", fontWeight: 500, fontSize: "1.1rem" }}>
              3. Implied spread — the common yardstick
            </strong>
            <p style={{ marginTop: 10, opacity: 0.75, lineHeight: 1.6 }}>
              Yearly euros ÷ energy sold = the implied spread, in €/MWh. Whether
              the battery is 200 kWh or 350 kWh, the spread is the same yardstick —
              the price gap captured per unit of energy.
            </p>
          </div>
        </div>
      </section>

      {/* Limitations */}
      <section className="kw-section kw-section--bone kw-section--tight">
        <div className="kw-section__inner">
          <Eyebrow>Limitations</Eyebrow>
          <ul className="kw-diligence__list" style={{ marginTop: 18 }}>
            <DiligenceItem body="Day-ahead prices only — faster intraday and balancing-market trades are not included." />
            <DiligenceItem body="The battery is assumed to lose 2% of its capacity each year." />
            <DiligenceItem body="The realistic strategy follows a simple 28-day rule. Real operators forecast more cleverly." />
            <DiligenceItem body="Grid fees use a simplified model. Real German fees vary by region and voltage level." />
            <DiligenceItem body="Grid-stability payments (FCR, aFRR) are excluded — this is buy-low, sell-high only." />
            <DiligenceItem body="The model assumes one full cycle a day. Cycling more often could capture more." />
          </ul>
        </div>
      </section>

      <footer className="kw-footer">
        <Eyebrow>Source data</Eyebrow>
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

function DiligenceItem({ body }: { body: string }) {
  return (
    <li className="kw-diligence__item" style={{ borderBottom: "none", paddingBottom: 8 }}>
      <span style={{ opacity: 0.72, fontSize: "0.92rem" }}>{body}</span>
    </li>
  );
}
