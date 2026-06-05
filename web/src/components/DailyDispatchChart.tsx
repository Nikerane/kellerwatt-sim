import { scaleLinear } from "d3-scale";
import type { DayDetailResponse } from "../data/playground";
import { DataMono } from "./DataMono";
import { Eyebrow } from "./Eyebrow";

const W = 360;
const H = 240;
const M = { top: 14, right: 44, bottom: 34, left: 44 };
const HOUR_TICKS = [0, 6, 12, 18, 24];

/** Aggregate per-interval arrays into 24 hourly buckets. */
function aggregateHourly(
  prices: number[],
  charge_kw: number[],
  discharge_kw: number[],
  dt_h: number,
  numIntervals: number,
) {
  const intervalsPerHour = Math.max(1, Math.round(1 / dt_h));
  const hourly: { price: number; chargeKwh: number; dischargeKwh: number }[] = [];

  for (let h = 0; h < 24; h++) {
    let priceSum = 0;
    let chargeEnergy = 0;
    let dischargeEnergy = 0;
    let count = 0;

    const start = h * intervalsPerHour;
    const end = Math.min((h + 1) * intervalsPerHour, numIntervals);
    for (let i = start; i < end; i++) {
      if (i < prices.length) {
        priceSum += prices[i];
        chargeEnergy += (charge_kw[i] ?? 0) * dt_h;
        dischargeEnergy += (discharge_kw[i] ?? 0) * dt_h;
        count++;
      }
    }

    hourly.push({
      price: count > 0 ? priceSum / count : 0,
      chargeKwh: chargeEnergy,
      dischargeKwh: dischargeEnergy,
    });
  }
  return hourly;
}

interface Props {
  data: DayDetailResponse;
  strategy: "ceiling" | "causal";
}

export function DailyDispatchChart({ data, strategy }: Props) {
  const detail = data[strategy];
  const hourly = aggregateHourly(
    data.prices, detail.charge_kw, detail.discharge_kw,
    data.dt_h, data.num_intervals,
  );

  // Price domain
  const priceMin = Math.min(0, ...hourly.map((h) => h.price));
  const priceMaxRaw = Math.max(...hourly.map((h) => h.price), 1);
  const priceMax = Math.ceil(priceMaxRaw / 20) * 20 + 20;

  // Power domain — symmetric around zero
  const maxEnergy = Math.max(
    ...hourly.map((h) => Math.max(h.chargeKwh, h.dischargeKwh)),
    1,
  );
  const powerExtent = Math.max(Math.ceil(maxEnergy / 5) * 5, 10);

  const x = scaleLinear().domain([0, 23]).range([M.left, W - M.right]);
  const yPrice = scaleLinear().domain([priceMin, priceMax]).range([H - M.bottom, M.top]);
  const yPower = scaleLinear().domain([-powerExtent, powerExtent]).range([H - M.bottom, M.top]);
  const baseline = yPower(0);

  const barW = Math.max(2, ((W - M.left - M.right) / 24) * 0.7);

  // Price path
  const pricePts = hourly
    .map((h, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${yPrice(h.price).toFixed(1)}`)
    .join(" ");

  const tone = strategy === "ceiling" ? "ember" : "muted";
  const title = strategy === "ceiling"
    ? "Best-case (perfect info)"
    : "Realistic (actual strategy)";

  const avgBuy = detail.avg_buy_price !== null
    ? `€${detail.avg_buy_price.toFixed(1)}`
    : "—";
  const avgSell = detail.avg_sell_price !== null
    ? `€${detail.avg_sell_price.toFixed(1)}`
    : "—";
  const boughtKWh = detail.mwh_charged * 1000;
  const soldKWh = detail.mwh_discharged * 1000;

  return (
    <div className="kw-card" style={{ padding: "20px 24px 16px" }}>
      <span style={{ display: "block", marginBottom: 10 }}>
        <Eyebrow>{title}</Eyebrow>
      </span>

      <p style={{
        fontSize: "0.82rem",
        fontFamily: "var(--mono)",
        lineHeight: 1.5,
        margin: 0,
        color: "var(--slate)",
      }}>
        Bought{" "}
        <DataMono tone="muted" size="sm">{boughtKWh.toFixed(0)} kWh</DataMono>
        {" "}@ avg {avgBuy}{"  "}→ Sold{" "}
        <DataMono tone="muted" size="sm">{soldKWh.toFixed(0)} kWh</DataMono>
        {" "}@ avg {avgSell}
        {"  "}| Net:{" "}
        <DataMono tone={tone} size="sm">€{detail.gross_eur.toFixed(2)}</DataMono>
      </p>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`${title}: bought ${boughtKWh.toFixed(0)} kWh, sold ${soldKWh.toFixed(0)} kWh, net €${detail.gross_eur.toFixed(2)}`}
        style={{ width: "100%", marginTop: 12 }}
      >
        {/* Price line (faint, behind bars) */}
        <path d={pricePts} fill="none" stroke="var(--slate)" strokeWidth={1.5} opacity={0.16} />

        {/* Zero-price line */}
        <line x1={M.left} x2={W - M.right} y1={yPrice(0)} y2={yPrice(0)}
          stroke="var(--slate)" strokeWidth={0.5} opacity={0.10} strokeDasharray="3,5" />

        {/* Zero-power baseline */}
        <line x1={M.left} x2={W - M.right} y1={baseline} y2={baseline}
          stroke="var(--slate)" strokeWidth={0.5} opacity={0.18} />

        {/* Hourly bars — charge above baseline, discharge below */}
        {hourly.map((h, i) => {
          const cx = x(i);
          const above = h.chargeKwh > 0.001
            ? yPower(h.chargeKwh)
            : baseline;
          const below = h.dischargeKwh > 0.001
            ? yPower(-h.dischargeKwh)
            : baseline;

          return (
            <g key={i}>
              {h.chargeKwh > 0.001 && (
                <rect
                  x={cx - barW / 2}
                  y={above}
                  width={barW}
                  height={baseline - above}
                  fill="var(--clay-red)"
                  opacity={0.75}
                  rx={1.5}
                />
              )}
              {h.dischargeKwh > 0.001 && (
                <rect
                  x={cx - barW / 2}
                  y={baseline}
                  width={barW}
                  height={below - baseline}
                  fill="#4CAF50"
                  opacity={0.75}
                  rx={1.5}
                />
              )}
            </g>
          );
        })}

        {/* Price max label on right axis */}
        <text x={W - M.right + 28} y={yPrice(priceMax) + 4}
          textAnchor="start" fill="var(--slate)" opacity={0.28}
          fontSize={9} fontFamily="var(--mono)">
          €{priceMax.toFixed(0)}
        </text>

        {/* Hour labels */}
        {HOUR_TICKS.map((h) => {
          const tickX = h === 24 ? W - M.right : x(h);
          const anchor = h === 0 ? "start" : h === 24 ? "end" : "middle";
          return (
            <text key={h} x={tickX} y={H - M.bottom + 16}
              textAnchor={anchor} fill="var(--slate)" opacity={0.35}
              fontSize={10} fontFamily="var(--mono)">
              {h}h
            </text>
          );
        })}
      </svg>

      <div style={{
        display: "flex", gap: 22, marginTop: 6,
        fontSize: "0.70rem", opacity: 0.55, fontFamily: "var(--sans)",
      }}>
        <span>
          <span style={{ display: "inline-block", width: 10, height: 10,
            background: "var(--clay-red)", borderRadius: 2, verticalAlign: "middle", marginRight: 4 }} />
          Charging
        </span>
        <span>
          <span style={{ display: "inline-block", width: 10, height: 10,
            background: "#4CAF50", borderRadius: 2, verticalAlign: "middle", marginRight: 4 }} />
          Discharging
        </span>
        <span>
          <span style={{ display: "inline-block", width: 14,
            borderTop: "1.5px solid var(--slate)", verticalAlign: "middle",
            marginRight: 4, opacity: 0.25 }} />
          Price
        </span>
      </div>
    </div>
  );
}
