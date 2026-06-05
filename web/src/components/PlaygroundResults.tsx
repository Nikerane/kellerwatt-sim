import { DataMono } from "./DataMono";
import type { SolveResponse } from "../data/playground";
import { euro, eurPerMwh, cycles } from "../data/load";

interface Props {
  data: SolveResponse;
  year: number;
}

interface Col {
  key: string;
  title: string;
  sub: string;
  tone: "ember" | "muted" | "neutral";
  spread: number | null;
  annual: number | null;
  cyclesPerDay: number | null;
}

/** Four-column case table for live-solved playground results. Matches the
    honesty page CaseTable layout but reads from a SolveResponse. */
export function PlaygroundResults({ data, year }: Props) {
  const yr = String(year);
  const ceil = data.ceiling[yr];
  const causalR = data.causal_retained[yr];
  const causalL = data.causal_lost[yr];

  const cols: Col[] = [
    {
      key: "assumed",
      title: "Assumed",
      sub: "your inputs",
      tone: "muted",
      spread: data.assumed.spread_eur_mwh,
      annual: data.assumed.gross_eur,
      cyclesPerDay: data.assumed.cycles_per_day,
    },
    {
      key: "ceiling",
      title: "Best-case",
      sub: "perfect info",
      tone: "ember",
      spread: ceil?.spread_eur_mwh ?? null,
      annual: ceil?.gross_eur ?? null,
      cyclesPerDay: ceil?.cycles_ac ?? null,
    },
    {
      key: "causal-retained",
      title: "Realistic",
      sub: "exemption retained",
      tone: "neutral",
      spread: causalR?.spread_eur_mwh ?? null,
      annual: causalR?.gross_eur ?? null,
      cyclesPerDay: causalR?.cycles_ac ?? null,
    },
    {
      key: "causal-lost",
      title: "Conservative",
      sub: "exemption lost",
      tone: "neutral",
      spread: causalL?.spread_eur_mwh ?? null,
      annual: causalL?.gross_eur ?? null,
      cyclesPerDay: causalL?.cycles_ac ?? null,
    },
  ];

  const valCls = (c: Col) =>
    c.key === "ceiling" ? "kw-table__col-validated" : "";

  return (
    <table className="kw-table" style={{ marginTop: 32 }}>
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
              <DataMono tone={c.tone === "ember" ? "ember" : "neutral"}>
                {euro(c.annual)}
              </DataMono>
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
      </tbody>
    </table>
  );
}
