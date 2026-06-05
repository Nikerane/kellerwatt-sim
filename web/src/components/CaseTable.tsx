import { DataMono } from "./DataMono";
import {
  results,
  strategy,
  scenario,
  yearOf,
  euro,
  eurPerMwh,
  cycles,
} from "../data/load";
import type { Metric } from "../data/types";

type Tone = "neutral" | "ember" | "muted";

interface Col {
  key: string;
  title: string;
  sub: string;
  status: "validated" | "estimate" | null;
  tone: Tone;
  spread: number | null;
  annual: number | null;
  cyclesPerDay: number | null;
  irr: Metric | null;
  payback: Metric | null;
}

/** The case table (B3). Cases are columns; metrics are rows. The validated ceiling
    is the single Ember signal. IRR/payback for the causal cases carry the
    methodology label and a "provisional" tag — never a fabricated number. */
export function CaseTable({ year }: { year: number }) {
  const bp = results.assumptions.business_plan;
  const ceil = yearOf(strategy("lp_ceiling"), year);
  const causalYear = yearOf(strategy("causal_walkforward"), year);
  const retained = scenario("causal_exemption_retained");
  const lost = scenario("causal_exemption_lost");

  const cols: Col[] = [
    {
      key: "assumed",
      title: "Assumed",
      sub: "business plan",
      status: null,
      tone: "muted",
      spread: bp.assumed_spread_eur_mwh,
      annual: bp.assumed_gross_eur,
      cyclesPerDay: bp.assumed_cycles_per_day,
      irr: null,
      payback: null,
    },
    {
      key: "ceiling",
      title: "Ceiling",
      sub: "perfect foresight",
      status: "validated",
      tone: "ember",
      spread: ceil.ceiling_eur_mwh,
      annual: ceil.gross_eur,
      cyclesPerDay: ceil.cycles_ac,
      irr: null,
      payback: null,
    },
    {
      key: "causal",
      title: "Causal",
      sub: "walk-forward",
      status: "estimate",
      tone: "neutral",
      spread: retained.implied_spread.value,
      annual: retained.net_annual_eur,
      cyclesPerDay: causalYear.cycles_ac,
      irr: retained.irr,
      payback: retained.payback_years,
    },
    {
      key: "lost",
      title: "Conservative",
      sub: "exemption lost",
      status: "estimate",
      tone: "neutral",
      spread: lost.implied_spread.value,
      annual: lost.net_annual_eur,
      cyclesPerDay: causalYear.cycles_ac,
      irr: lost.irr,
      payback: lost.payback_years,
    },
  ];

  const valCls = (c: Col) => (c.status === "validated" ? "kw-table__col-validated" : "");

  return (
    <table className="kw-table">
      <caption className="kw-eyebrow" style={{ marginBottom: 18 }}>
        Captured spread · {year}
      </caption>
      <thead>
        <tr>
          <th scope="col" aria-label="metric" />
          {cols.map((c) => (
            <th scope="col" key={c.key} className={valCls(c)}>
              {c.title}
              <span className="kw-table__row-note">{c.sub}</span>
              {c.status && <span className={`kw-status kw-status--${c.status}`}>{c.status}</span>}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row">
            Implied spread
            <span className="kw-table__row-note">€ / MWh discharged</span>
          </th>
          {cols.map((c) => (
            <td key={c.key} className={valCls(c)}>
              <DataMono tone={c.tone} size="lg">
                {eurPerMwh(c.spread)}
              </DataMono>
            </td>
          ))}
        </tr>
        <tr>
          <th scope="row">
            Annual figure
            <span className="kw-table__row-note">gross / net per year</span>
          </th>
          {cols.map((c) => (
            <td key={c.key} className={valCls(c)}>
              <DataMono tone={c.tone === "ember" ? "ember" : "neutral"}>{euro(c.annual)}</DataMono>
            </td>
          ))}
        </tr>
        <tr>
          <th scope="row">
            Cycles / day
            <span className="kw-table__row-note">AC delivered</span>
          </th>
          {cols.map((c) => (
            <td key={c.key} className={valCls(c)}>
              <DataMono tone="muted">{cycles(c.cyclesPerDay)}</DataMono>
            </td>
          ))}
        </tr>
        <tr>
          <th scope="row">
            Project IRR
            <span className="kw-table__row-note">constant-EBITDA</span>
          </th>
          {cols.map((c) => (
            <td key={c.key} className={valCls(c)}>
              <ProvisionalCell metric={c.irr} fmt={(v) => `${(v * 100).toFixed(1)}%`} />
            </td>
          ))}
        </tr>
        <tr>
          <th scope="row">
            Payback
            <span className="kw-table__row-note">years</span>
          </th>
          {cols.map((c) => (
            <td key={c.key} className={valCls(c)}>
              <ProvisionalCell metric={c.payback} fmt={(v) => `${v.toFixed(1)} yr`} />
            </td>
          ))}
        </tr>
      </tbody>
    </table>
  );
}

function ProvisionalCell({
  metric,
  fmt,
}: {
  metric: Metric | null;
  fmt: (v: number) => string;
}) {
  if (!metric) return <DataMono tone="muted">—</DataMono>;
  return (
    <span title={metric.methodology_label}>
      <DataMono tone="muted">{metric.value === null ? "—" : fmt(metric.value)}</DataMono>
      <span className={`kw-status kw-status--${metric.status}`}>{metric.status}</span>
    </span>
  );
}
