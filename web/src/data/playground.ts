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

/** Shape of the POST /day-detail response — per-interval dispatch arrays. */
export interface StrategyDayDetail {
  gross_eur: number;
  mwh_discharged: number;
  mwh_charged: number;
  avg_buy_price: number | null;
  avg_sell_price: number | null;
  charge_kw: number[];
  discharge_kw: number[];
  soc_kwh: number[];
}

export interface DayDetailResponse {
  date: string;
  num_intervals: number;
  dt_h: number;
  prices: number[];
  best_date: string;
  worst_date: string;
  available_dates: string[];
  ceiling: StrategyDayDetail;
  causal: StrategyDayDetail;
}
