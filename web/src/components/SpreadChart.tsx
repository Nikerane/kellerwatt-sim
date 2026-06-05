import { scaleLinear, scalePoint } from "d3-scale";
import { strategy, yearOf, results, YEARS } from "../data/load";

const W = 720;
const H = 440;
const M = { top: 28, right: 28, bottom: 52, left: 56 };

function linePath(pts: Array<[number, number]>): string {
  return pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
}

/** Widening-spread chart (B4). Best-case vs realistic benchmark,
    2023→2025, with the €80 assumption as a dashed reference and the bracket
    between the two strategies shaded. Hand-rolled SVG on d3 scales — no chart lib.
    Lives on a Hearth section, so it reads light-on-dark. */
export function SpreadChart() {
  const years = YEARS;
  const assumed = results.assumptions.business_plan.assumed_spread_eur_mwh;
  const ceiling = years.map((y) => yearOf(strategy("lp_ceiling"), y).ceiling_eur_mwh ?? 0);
  const causal = years.map((y) => yearOf(strategy("causal_walkforward"), y).causal_eur_mwh ?? 0);

  const yMax = Math.ceil((Math.max(assumed, ...ceiling) + 6) / 10) * 10;
  const x = scalePoint<string>().domain(years.map(String)).range([M.left, W - M.right]).padding(0.5);
  const y = scaleLinear().domain([0, yMax]).range([H - M.bottom, M.top]);

  const px = (i: number) => x(String(years[i]))!;
  const ceilPts = ceiling.map((v, i) => [px(i), y(v)] as [number, number]);
  const causPts = causal.map((v, i) => [px(i), y(v)] as [number, number]);
  const bracket = linePath(ceilPts) + " " + linePath([...causPts].reverse()).replace("M", "L") + " Z";
  const yTicks = [0, 20, 40, 60, 80].filter((t) => t <= yMax);

  return (
    <div className="kw-chart">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={
          `Captured spread by year. Assumed €${assumed} per MWh. ` +
          years
            .map((yr, i) => `${yr}: best €${ceiling[i].toFixed(1)}, real €${causal[i].toFixed(1)}`)
            .join("; ") +
          "."
        }
      >
        {/* y gridlines + labels */}
        {yTicks.map((t) => (
          <g key={t}>
            <line className="kw-chart__grid" x1={M.left} x2={W - M.right} y1={y(t)} y2={y(t)} />
            <text className="kw-chart__axis" x={M.left - 12} y={y(t)} dy="0.32em" textAnchor="end">
              {t}
            </text>
          </g>
        ))}

        {/* shaded bracket between best and real */}
        <path className="kw-chart__bracket" d={bracket} />

        {/* assumed €80 reference */}
        <line className="kw-chart__assumed" x1={M.left} x2={W - M.right} y1={y(assumed)} y2={y(assumed)} />
        <text className="kw-chart__axis" x={W - M.right} y={y(assumed) - 8} textAnchor="end">
          €{assumed} assumed
        </text>

        {/* best + real lines */}
        <path className="kw-chart__causal" d={linePath(causPts)} />
        <path className="kw-chart__ceiling" d={linePath(ceilPts)} />

        {/* best-case points with value labels (the Ember signal) */}
        {ceilPts.map(([cx, cy], i) => (
          <g key={i}>
            <circle className="kw-chart__dot" cx={cx} cy={cy} r={4.5} />
            <text
              className="kw-chart__axis"
              x={cx}
              y={cy - 14}
              textAnchor="middle"
              style={{ fill: "var(--ember)", fontSize: 13 }}
            >
              €{ceiling[i].toFixed(1)}
            </text>
          </g>
        ))}
        {causPts.map(([cx, cy], i) => (
          <text key={i} className="kw-chart__axis" x={cx} y={cy + 20} textAnchor="middle">
            €{causal[i].toFixed(1)}
          </text>
        ))}

        {/* x labels */}
        {years.map((yr, i) => (
          <text key={yr} className="kw-chart__axis" x={px(i)} y={H - M.bottom + 26} textAnchor="middle">
            {yr}
          </text>
        ))}
      </svg>

      <div className="kw-chart__legend">
        <span>
          <span className="kw-chart__swatch" style={{ borderColor: "var(--ember)" }} />
          Best-case (perfect info)
        </span>
        <span>
          <span className="kw-chart__swatch" style={{ borderColor: "rgba(245,241,234,0.85)" }} />
          Realistic strategy
        </span>
        <span>
          <span
            className="kw-chart__swatch"
            style={{ borderColor: "rgba(245,241,234,0.45)", borderTopStyle: "dashed" }}
          />
          €{assumed} assumed
        </span>
      </div>
    </div>
  );
}
