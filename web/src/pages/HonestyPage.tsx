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
          <Eyebrow ember>Validated on real German power prices</Eyebrow>
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
          A battery earns by buying power when it's cheap and selling when it's
          dear; the gap it keeps is the spread. Even one that could see a whole
          day's prices in advance captured only{" "}
          <DataMono tone="ember">{eurPerMwh(ceilMin)}</DataMono>–
          <DataMono tone="ember">{eurPerMwh(ceilMax)}</DataMono> per MWh — every
          year, {YEARS[0]} to {latest}. Always under the €80 the business plan
          assumed. A real battery, blind to tomorrow, keeps less. Below: what
          we've proven, what's still an estimate, and what we're still checking.
        </p>
        <div className="kw-hero__meta kw-fade kw-fade--3">
          <Stat label="Best case captured" value={`${eurPerMwh(ceilMin)}–${eurPerMwh(ceilMax)}`} ember />
          <Stat label="Price history" value={`${YEARS[0]}–${latest}`} />
          <Stat label="Realistic vs best case" value={`${capLo}–${capHi}%`} />
          <Stat label="Days backtested" value={(YEARS.length * 365).toLocaleString()} />
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
          Best case is the most a battery could earn if it knew every price in
          advance — a ceiling no real operator can beat, checked to the cent on
          real prices. Realistic is what a normal operator could actually earn.
          Conservative subtracts a grid fee we may owe if a tax exemption is lost.
          We leave the headline return and payback blank until two open questions
          close.
        </p>
        <div style={{ overflowX: "auto" }}>
          <CaseTable year={latest} />
        </div>
        <p className="kw-lead" style={{ marginTop: 24, fontSize: "0.92rem", opacity: 0.8 }}>
          The business plan claimed{" "}
          <DataMono tone="muted">{euro(9947)}</DataMono> a year. Run through the same
          formula — spread × energy × cycles × days — the €80 assumption is really worth{" "}
          <DataMono tone="muted">{euro(results.assumptions.business_plan.assumed_gross_eur)}</DataMono>
          , not €9,947.
        </p>
      </Section>

      {/* THE TREND — Hearth (chart reads light-on-dark) */}
      <Section tone="hearth">
        <Eyebrow>The spread, by year</Eyebrow>
        <Couplet
          first="The best case is rising."
          second="It has stayed under €80 every year."
          size="lg"
        />
        <div className="kw-split kw-split--chart" style={{ marginTop: 44 }}>
          <p className="kw-lead">
            The spread widened from {YEARS[0]} to {latest} as the grid took on more
            renewables and more hours of negative prices. Even so, the best case
            never reached the assumed €80 — and a real operator, blind to the day
            ahead, captured only {capLo}–{capHi}% of it.
          </p>
          <SpreadChart />
        </div>
      </Section>

      {/* DILIGENCE — Bone */}
      <Section tone="bone">
        <Eyebrow>Still checking</Eyebrow>
        <Couplet
          first="Two questions remain open."
          second="We are not hiding them."
          size="lg"
        />
        <ul className="kw-diligence__list" style={{ marginTop: 32 }}>
          <Diligence
            tag="#8"
            title="How the trading partner is paid"
            body="A licensed partner sells our power on the market and takes a fee. Whether that fee comes off revenue or off profit — and how we split the rest — is set by a signed contract, not by us. We've built all three fee variants; the real one is pending."
          />
          <Diligence
            tag="#9"
            title="The grid-fee waiver (§118(6))"
            body={`German law can waive a grid fee for storage. Whether we keep that waiver is a legal question — until a lawyer confirms it, the conservative case assumes we lose it and adds a €${results.assumptions.fees.grid_energy_fee_eur_mwh_charge || 30}/MWh charge on the power we draw.`}
          />
        </ul>
        <p className="kw-lead" style={{ marginTop: 28, fontSize: "0.92rem", opacity: 0.82 }}>
          Until both close, we leave the return and payback blank. A flat profit
          guess is not a real return.
        </p>
      </Section>

      <footer className="kw-footer">
        <Eyebrow>How this works</Eyebrow>
        <p style={{ marginTop: 14 }}>
          Every number here comes from running a solver (HiGHS — free,
          industry-standard) on real {p.price_zone} day-ahead prices from{" "}
          {p.data_source}, {p.years.join(" / ")}. For each day it finds the
          charge-and-sell schedule that earns the most. Best case assumes it knew
          that day's prices in advance; realistic uses only past data.
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
