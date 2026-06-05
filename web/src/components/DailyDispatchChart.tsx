import { scaleLinear } from "d3-scale";
import type { DayDetailResponse } from "../data/playground";
import { DataMono } from "./DataMono";
import { Eyebrow } from "./Eyebrow";

const W = 320;
const H = 280;
const M = { top: 20, right: 36, bottom: 38, left: 42 };

/** Build an SVG bar path for charge or discharge bars. */
function barPath(
  values: number[],
  x: (i: number) => number,
  y: (v: number) => number,
  baseline: number,
  barW: number,
): string {
  const parts: string[] = [];
  for (let i = 0; i < values.length; i++) {
    if (values[i] <= 0) continue;
    const bx = x(i) - barW / 2;
    const bw = barW;
    const vh = Math.abs(y(values[i]) - y(baseline));
    const by = Math.min(y(values[i]), y(baseline));
    parts.push(`M${bx.toFixed(1)},${by.toFixed(1)}h${bw.toFixed(1)}v${vh.toFixed(1)}h${-bw.toFixed(1)}Z`);
  }
  return parts.join("");
}

/** Build a stepped line path for price or SoC. */
function linePath(
  values: number[],
  x: (i: number) => number,
  y: (v: number) => number,
): string {
  const parts: string[] = [];
  for (let i = 0; i < values.length; i++) {
    const px = x(i);
    const py = y(values[i]);
    parts.push(`${i === 0 ? "M" : "L"}${px.toFixed(1)},${py.toFixed(1)}`);
  }
  return parts.join("");
}

interface Props {
  data: DayDetailResponse;
  strategy: "ceiling" | "causal";
}

export function DailyDispatchChart({ data, strategy }: Props) {
  const detail = data[strategy];
  const prices = data.prices;
  const N = data.num_intervals;

  // Price domain: start from 0 or below
  const priceMin = Math.floor(Math.min(0, ...(prices.length > 0 ? prices : [0])));
  const priceMax = Math.ceil(Math.max(...(prices.length > 0 ? prices : [50])) + 10);
  const kwMax = 50; // matched to the 50 kW slider default
  const socMax = 200; // matched to the 200 kWh slider default

  const x = scaleLinear().domain([0, Math.max(0, N - 1)]).range([M.left, W - M.right]);
  const yPrice = scaleLinear().domain([priceMin, priceMax]).range([H - M.bottom, M.top]);
  const yKw = scaleLinear().domain([0, kwMax]).range([H - M.bottom, M.top]);
  const ySoc = scaleLinear().domain([0, socMax]).range([H - M.bottom, M.top]);

  const barW = Math.max(1.2, ((W - M.left - M.right) / N) - 0.6);

  const priceD = linePath(prices, x, yPrice);
  const chargeD = barPath(detail.charge_kw, x, yKw, 0, barW);
  const dischargeD = barPath(detail.discharge_kw, x, yKw, 0, barW);
  const socD = detail.soc_kwh.length > 0
    ? linePath(detail.soc_kwh, x, ySoc)
    : "";

  const tone = strategy === "ceiling" ? "ember" : "muted";
  const title = strategy === "ceiling"
    ? "Ceiling (perfect foresight)"
    : "Causal (walk-forward)";

  const avgBuy = detail.avg_buy_price !== null
    ? `€${detail.avg_buy_price.toFixed(1)}`
    : "—";
  const avgSell = detail.avg_sell_price !== null
    ? `€${detail.avg_sell_price.toFixed(1)}`
    : "—";

  const boughtKWh = detail.mwh_charged * 1000;
  const soldKWh = detail.mwh_discharged * 1000;

  return (
    <div className="kw-card" style={{ padding: "20px 24px 18px" }}>
      <span style={{ display: "block", marginBottom: 12 }}>
        <Eyebrow>{title}</Eyebrow>
      </span>

      <p style={{
        fontSize: "0.80rem",
        fontFamily: "var(--mono)",
        lineHeight: 1.55,
        margin: 0,
        color: "var(--bone)",
      }}>
        Bought{" "}
        <DataMono tone="muted" size="sm">
          {boughtKWh.toFixed(0)} kWh
        </DataMono>
        {" "}@ avg {avgBuy}{" "}
        → Sold{" "}
        <DataMono tone="muted" size="sm">
          {soldKWh.toFixed(0)} kWh
        </DataMono>
        {" "}@ avg {avgSell}
        {" "}| Net:{" "}
        <DataMono tone={tone} size="sm">
          €{detail.gross_eur.toFixed(2)}
        </DataMono>
      </p>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`${title}: bought ${boughtKWh.toFixed(0)} kWh, sold ${soldKWh.toFixed(0)} kWh, net €${detail.gross_eur.toFixed(2)}`}
        style={{ width: "100%", marginTop: 14 }}
      >
        {/* Price line */}
        {priceD && (
          <path
            d={priceD}
            fill="none"
            stroke="rgba(245,241,234,0.35)"
            strokeWidth={1.3}
          />
        )}
        {/* Zero-price line */}
        <line
          x1={M.left}
          x2={W - M.right}
          y1={yPrice(0)}
          y2={yPrice(0)}
          stroke="rgba(245,241,234,0.15)"
          strokeWidth={0.5}
        />
        {/* Charge bars (red) */}
        {chargeD && (
          <path d={chargeD} fill="var(--clay-red)" opacity={0.7} />
        )}
        {/* Discharge bars (green) */}
        {dischargeD && (
          <path d={dischargeD} fill="#4CAF50" opacity={0.7} />
        )}
        {/* SoC dashed line */}
        {socD && (
          <path
            d={socD}
            fill="none"
            stroke="var(--ember)"
            strokeWidth={1.0}
            strokeDasharray="2,3"
            opacity={0.55}
          />
        )}
      </svg>

      <div style={{
        display: "flex",
        gap: 18,
        marginTop: 10,
        fontSize: "0.70rem",
        opacity: 0.55,
        fontFamily: "var(--sans)",
      }}>
        <span>
          <span style={{
            display: "inline-block",
            width: 10,
            height: 10,
            background: "var(--clay-red)",
            borderRadius: 2,
            verticalAlign: "middle",
            marginRight: 4,
          }} />
          Charge
        </span>
        <span>
          <span style={{
            display: "inline-block",
            width: 10,
            height: 10,
            background: "#4CAF50",
            borderRadius: 2,
            verticalAlign: "middle",
            marginRight: 4,
          }} />
          Discharge
        </span>
        <span>
          <span style={{
            display: "inline-block",
            width: 10,
            borderTop: "1.5px dashed var(--ember)",
            verticalAlign: "middle",
            marginRight: 4,
          }} />
          SoC
        </span>
      </div>
    </div>
  );
}
