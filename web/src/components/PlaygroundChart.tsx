import { scaleLinear, scalePoint } from "d3-scale";
import type { SolveResponse } from "../data/playground";

const W = 600;
const H = 300;
const M = { top: 20, right: 28, bottom: 44, left: 52 };

function linePath(pts: Array<[number, number]>): string {
  return pts
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`)
    .join(" ");
}

interface Props {
  data: SolveResponse;
}

/** Small SVG spread chart for live-solved playground results. Same design
    language as the honesty page SpreadChart but sized for the sidebar. */
export function PlaygroundChart({ data }: Props) {
  const years = data.years;
  const assumed = data.assumed.spread_eur_mwh;
  const ceiling = years.map((y) => data.ceiling[String(y)]?.spread_eur_mwh ?? 0);
  const causal = years.map(
    (y) => data.causal_retained[String(y)]?.spread_eur_mwh ?? 0,
  );

  const yMax = Math.ceil((Math.max(assumed, ...ceiling) + 6) / 10) * 10;
  const x = scalePoint<string>()
    .domain(years.map(String))
    .range([M.left, W - M.right])
    .padding(0.5);
  const y = scaleLinear()
    .domain([0, yMax])
    .range([H - M.bottom, M.top]);

  const px = (i: number) => x(String(years[i]))!;
  const ceilPts = ceiling.map((v, i) => [px(i), y(v)] as [number, number]);
  const causPts = causal.map((v, i) => [px(i), y(v)] as [number, number]);
  const bracket =
    linePath(ceilPts) +
    " " +
    linePath([...causPts].reverse()).replace("M", "L") +
    " Z";
  const yTicks = [0, 20, 40, 60, 80, 100, 120].filter((t) => t <= yMax);

  return (
    <div className="kw-chart" style={{ marginTop: 40 }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={
          `Playground spread chart. Assumed €${assumed}/MWh. ` +
          years
            .map(
              (yr, i) =>
                `${yr}: best €${ceiling[i].toFixed(1)}, real €${causal[i].toFixed(1)}`,
            )
            .join("; ") +
          "."
        }
      >
        {yTicks.map((t) => (
          <g key={t}>
            <line
              className="kw-chart__grid"
              x1={M.left}
              x2={W - M.right}
              y1={y(t)}
              y2={y(t)}
            />
            <text
              className="kw-chart__axis"
              x={M.left - 12}
              y={y(t)}
              dy="0.32em"
              textAnchor="end"
            >
              {t}
            </text>
          </g>
        ))}

        <path className="kw-chart__bracket" d={bracket} />

        <line
          className="kw-chart__assumed"
          x1={M.left}
          x2={W - M.right}
          y1={y(assumed)}
          y2={y(assumed)}
        />
        <text
          className="kw-chart__axis"
          x={W - M.right}
          y={y(assumed) - 8}
          textAnchor="end"
        >
          €{assumed} assumed
        </text>

        <path className="kw-chart__causal" d={linePath(causPts)} />
        <path className="kw-chart__ceiling" d={linePath(ceilPts)} />

        {ceilPts.map(([cx, cy], i) => {
          // stagger labels: even years above, odd years below — prevents overlap when values are close
          const above = i % 2 === 0;
          const ly = above ? cy - 14 : cy + 20;
          return (
            <g key={i}>
              <circle className="kw-chart__dot" cx={cx} cy={cy} r={4.5} />
              <text
                className="kw-chart__axis"
                x={cx}
                y={ly}
                textAnchor="middle"
                style={{ fill: "var(--ember)", fontSize: 13 }}
              >
                €{ceiling[i].toFixed(1)}
              </text>
            </g>
          );
        })}

        {causPts.map(([cx, cy], i) => (
          <g key={`causal-${i}`}>
            <circle className="kw-chart__dot" cx={cx} cy={cy} r={3} style={{ fill: "rgba(245,241,234,0.7)" }} />
            <text
              className="kw-chart__axis"
              x={cx}
              y={cy + 18}
              textAnchor="middle"
              style={{ fontSize: 11, opacity: 0.7 }}
            >
              €{causal[i].toFixed(1)}
            </text>
          </g>
        ))}

        {years.map((yr, i) => (
          <text
            key={yr}
            className="kw-chart__axis"
            x={px(i)}
            y={H - M.bottom + 26}
            textAnchor="middle"
          >
            {yr}
          </text>
        ))}
      </svg>

      <div className="kw-chart__legend">
        <span>
          <span
            className="kw-chart__swatch"
            style={{ borderColor: "var(--ember)" }}
          />
          Best-case
        </span>
        <span>
          <span
            className="kw-chart__swatch"
            style={{ borderColor: "rgba(245,241,234,0.85)" }}
          />
          Realistic
        </span>
        <span>
          <span
            className="kw-chart__swatch"
            style={{
              borderColor: "rgba(245,241,234,0.45)",
              borderTopStyle: "dashed",
            }}
          />
          Assumed
        </span>
      </div>
    </div>
  );
}
