import type { ReactNode } from "react";
import { Eyebrow } from "../components/Eyebrow";
import { Couplet } from "../components/Couplet";
import { DataMono } from "../components/DataMono";
import { CaseTable } from "../components/CaseTable";
import { SpreadChart } from "../components/SpreadChart";
import { SiteNav } from "../components/SiteNav";
import {
  results,
  strategy,
  euro,
  eurPerMwh,
  captureOfCeiling,
  YEARS,
} from "../data/load";

function Section({
  tone,
  children,
  className = "",
}: {
  tone: "hearth" | "bone";
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`kw-section kw-section--${tone} ${className}`.trim()}>
      <div className="kw-section__inner">{children}</div>
    </section>
  );
}

export function HonestyPage() {
  const ceilingYears = strategy("lp_ceiling").years;
  const ceilSpreads = ceilingYears.map((y) => y.ceiling_eur_mwh ?? 0);
  const ceilMin = Math.min(...ceilSpreads);
  const ceilMax = Math.max(...ceilSpreads);
  const latest = Math.max(...YEARS);
  const captures = YEARS.map(captureOfCeiling).filter((v): v is number => v !== null);
  const capLo = Math.round(Math.min(...captures) * 100);
  const capHi = Math.round(Math.max(...captures) * 100);
  const p = results.provenance;

  return (
    <main className="kw-page">
      <SiteNav current="honesty" />
      {/* HERO — Hearth */}
      <Section tone="hearth">
        <div className="kw-fade">
          <Eyebrow ember>Validated on real DE-LU prices</Eyebrow>
        </div>
        <div className="kw-fade kw-fade--2" style={{ marginTop: 28 }}>
          <Couplet
            as="h1"
            size="xl"
            first="We assumed €80 a megawatt-hour."
            second="Real prices never got there."
          />
        </div>
        <p className="kw-lead kw-fade kw-fade--3" style={{ marginTop: 28 }}>
          A perfect-foresight battery on German day-ahead prices captured{" "}
          <DataMono tone="ember">{eurPerMwh(ceilMin)}</DataMono>–
          <DataMono tone="ember">{eurPerMwh(ceilMax)}</DataMono> per MWh every year from{" "}
          {YEARS[0]} to {latest} — always under the €80 the deck assumed. A causal strategy
          with no foresight captures less still. This page separates what is validated from
          what is only an estimate, and names what is still in diligence.
        </p>
        <div className="kw-hero__meta kw-fade kw-fade--3">
          <Stat label="Validated ceiling" value={`${eurPerMwh(ceilMin)}–${eurPerMwh(ceilMax)}`} ember />
          <Stat label="Years backtested" value={String(YEARS.length)} />
          <Stat label="Causal of ceiling" value={`${capLo}–${capHi}%`} />
          <Stat label="Simultaneity" value="0" />
        </div>
      </Section>

      {/* THE NUMBERS — Bone (honesty panel = daylight) */}
      <Section tone="bone">
        <Eyebrow>The four cases</Eyebrow>
        <Couplet
          first="Here is the assumption."
          second="Here is what the market actually paid."
          size="lg"
        />
        <p className="kw-lead" style={{ marginTop: 20, marginBottom: 36 }}>
          The ceiling is the most a battery could earn with perfect foresight — an upper
          bound, validated to the decimal on real prices. The causal case is a backtested
          estimate; the conservative case adds the grid fee owed if the §118(6) exemption is
          lost. IRR and payback stay blank until two diligence items land.
        </p>
        <div style={{ overflowX: "auto" }}>
          <CaseTable year={latest} />
        </div>
        <p className="kw-lead" style={{ marginTop: 24, fontSize: "0.92rem", opacity: 0.8 }}>
          The deck claimed{" "}
          <DataMono tone="muted">{euro(9947)}</DataMono> gross a year. Reconciled from the same
          identity — spread × usable MWh × cycles × days — the €80 assumption is worth{" "}
          <DataMono tone="muted">{euro(results.assumptions.business_plan.assumed_gross_eur)}</DataMono>
          , not €9,947.
        </p>
      </Section>

      {/* THE TREND — Hearth (chart reads light-on-dark) */}
      <Section tone="hearth">
        <Eyebrow>The spread, by year</Eyebrow>
        <Couplet
          first="The ceiling is rising."
          second="It has stayed under €80 every year."
          size="lg"
        />
        <div className="kw-split kw-split--chart" style={{ marginTop: 44 }}>
          <p className="kw-lead">
            Day-ahead spreads widened from {YEARS[0]} to {latest} as the system absorbed more
            renewables and more negative-price hours. Even so, the perfect-foresight ceiling
            never reached the assumed €80 — and a causal operator, blind to the day ahead,
            captured only {capLo}–{capHi}% of that ceiling.
          </p>
          <SpreadChart />
        </div>
      </Section>

      {/* DILIGENCE — Bone */}
      <Section tone="bone">
        <Eyebrow>Still in diligence</Eyebrow>
        <Couplet
          first="Two questions remain open."
          second="We are not hiding them."
          size="lg"
        />
        <ul className="kw-diligence__list" style={{ marginTop: 32 }}>
          <Diligence
            tag="#8"
            title="Aggregator term sheet"
            body="The BKV fee basis — turnover or net margin — and the revenue share come from a real aggregator term sheet, not code. The three fee bases are implemented and tested; the actual one is pending."
          />
          <Diligence
            tag="#9"
            title="§118(6) EnWG legal memo"
            body={`Whether the grid-fee exemption is retained or lost is a legal question. The conservative case applies a provisional €${results.assumptions.fees.grid_energy_fee_eur_mwh_charge || 30}/MWh charge on energy drawn, pending the memo.`}
          />
        </ul>
        <p className="kw-lead" style={{ marginTop: 28, fontSize: "0.92rem", opacity: 0.82 }}>
          Until both land, project IRR and payback are labelled{" "}
          <span className="kw-status kw-status--provisional">provisional</span> and shown blank —
          a constant-EBITDA placeholder is not a return.
        </p>
      </Section>

      <footer className="kw-footer">
        <Eyebrow>Provenance</Eyebrow>
        <p style={{ marginTop: 14 }}>
          {p.data_source} {p.price_zone} day-ahead prices, {p.years.join(" / ")}. Solver{" "}
          <DataMono tone="muted" size="sm">
            {results.solver.name} {results.solver.version}
          </DataMono>
          , status {results.solver.status}. Generated{" "}
          <DataMono tone="muted" size="sm">
            {p.generated_utc}
          </DataMono>
          {p.git_commit ? (
            <>
              {" "}
              · build{" "}
              <DataMono tone="muted" size="sm">
                {p.git_commit.slice(0, 10)}
              </DataMono>
            </>
          ) : null}
          . Schema v{results.schema_version}. {p.note}
        </p>
      </footer>
    </main>
  );
}

function Stat({ label, value, ember = false }: { label: string; value: string; ember?: boolean }) {
  return (
    <span style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <Eyebrow>{label}</Eyebrow>
      <DataMono tone={ember ? "ember" : "neutral"} size="lg">
        {value}
      </DataMono>
    </span>
  );
}

function Diligence({ tag, title, body }: { tag: string; title: string; body: string }) {
  return (
    <li className="kw-diligence__item">
      <span className="kw-diligence__tag">
        <DataMono tone="muted" size="sm">
          {tag}
        </DataMono>
      </span>
      <span>
        <strong style={{ fontFamily: "var(--serif)", fontWeight: 500, fontSize: "1.15rem" }}>
          {title}
        </strong>
        <span style={{ display: "block", marginTop: 6, opacity: 0.82 }}>{body}</span>
      </span>
    </li>
  );
}
