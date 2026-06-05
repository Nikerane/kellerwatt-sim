import { results } from "./load";

// Commit the artifact was generated at — used to deep-link the exact engine source.
const COMMIT = results.provenance.git_commit ?? "main";
const REPO = "https://github.com/Nikerane/kellerwatt-sim";

export const LINKS = {
  energyChartsApi: "https://api.energy-charts.info/price?bzn=DE-LU",
  energyCharts: "https://energy-charts.info/",
  energyChartsDocs: "https://api.energy-charts.info/",
  enwg118: "https://www.gesetze-im-internet.de/enwg_2005/__118.html",
  repo: REPO,
  commit: `${REPO}/commit/${COMMIT}`,
  highs: "https://highs.dev/",
  pulp: "https://coin-or.github.io/pulp/",
  schema: `${REPO}/blob/${COMMIT}/engine/schema/sim_results.schema.json`,
} as const;

/** Deep-link to an engine source file at the pinned commit. */
export function engineFile(path: string): string {
  return `${REPO}/blob/${COMMIT}/engine/${path}`;
}
