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
}

/** The case table (B3). Cases are columns; metrics are rows. The validated best-case
    is the single Ember signal. */
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
    },
    {
      key: "ceiling",
      title: "Best-case",
      sub: "sees the future",
      status: "validated",
      tone: "ember",
      spread: ceil.ceiling_eur_mwh,
      annual: ceil.gross_eur,
      cyclesPerDay: ceil.cycles_ac,
    },
    {
      key: "causal",
      title: "Realistic",
      sub: "waiver kept",
      status: "estimate",
      tone: "neutral",
      spread: retained.implied_spread.value,
      annual: retained.net_annual_eur,
      cyclesPerDay: causalYear.cycles_ac,
    },
    {
      key: "lost",
      title: "Conservative",
      sub: "waiver lost",
      status: "estimate",
      tone: "neutral",
      spread: lost.implied_spread.value,
      annual: lost.net_annual_eur,
      cyclesPerDay: causalYear.cycles_ac,
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
            <span className="kw-table__row-note">price gap per MWh</span>
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
            <span className="kw-table__row-note">euros per year</span>
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
            <span className="kw-table__row-note">full cycles</span>
          </th>
          {cols.map((c) => (
            <td key={c.key} className={valCls(c)}>
              <DataMono tone="muted">{cycles(c.cyclesPerDay)}</DataMono>
            </td>
          ))}
        </tr>
      </tbody>
    </table>
  );
}
