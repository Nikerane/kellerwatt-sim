/** Shape of the POST /solve response from the HF Spaces backend. */
export interface YearResult {
  spread_eur_mwh: number | null;
  gross_eur: number | null;
  cycles_ac: number | null;
}

export interface SolveResponse {
  schema_version: string;
  years: number[];
  assumed: {
    spread_eur_mwh: number;
    gross_eur: number;
    cycles_per_day: number;
  };
  ceiling: Record<string, YearResult>;
  causal_retained: Record<string, YearResult>;
  causal_lost: Record<string, YearResult>;
}
