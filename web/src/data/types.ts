// Mirrors engine/schema/sim_results.schema.json. The page only consumes the
// sanitized artifact (dist/sanitized -> src/data/sim_results.json).

export type Status = "validated" | "estimate" | "provisional";

export interface Metric {
  value: number | null;
  unit: string;
  methodology_label: string;
  status: Status;
}

export interface YearResult {
  year: number;
  ceiling_eur_mwh: number | null;
  causal_eur_mwh: number | null;
  cycles_ac: number | null;
  cycles_cell: number | null;
  gross_eur: number | null;
  mwh_discharged: number | null;
  day_count: number;
  simul_max: number | null;
  neg_price_cashflow_eur: number | null;
}

export interface MarketYear {
  year: number;
  negative_intervals: number;
  price_min: number;
  price_max: number;
  day_count: number;
}

export interface Strategy {
  id: "lp_ceiling" | "causal_walkforward";
  methodology_label: string;
  status: Status;
  years: YearResult[];
}

export interface Scenario {
  id: "causal_exemption_retained" | "causal_exemption_lost";
  label: string;
  grid_energy_fee_eur_mwh_charge: number;
  net_annual_eur: number | null;
  implied_spread: Metric;
  irr: Metric;
  payback_years: Metric;
}

export interface SimResults {
  schema_version: string;
  provenance: {
    price_zone: string;
    data_source: string;
    source_url?: string;
    years: number[];
    generated_utc: string;
    git_commit: string | null;
    note?: string;
  };
  solver: { name: string; version: string; status: string; mip_gap_tolerance: number | null };
  assumptions: {
    battery: Record<string, number>;
    business_plan: {
      assumed_spread_eur_mwh: number;
      assumed_cycles_per_day: number;
      assumed_gross_eur: number;
    };
    cycle_cap_per_day: number | null;
    operating_days: number;
    ancillary_eur: number;
    fees: { bkv_fee_basis: string; bkv_fee_rate: number; grid_energy_fee_eur_mwh_charge: number };
  };
  strategies: Strategy[];
  scenarios: Scenario[];
  market: MarketYear[];
}
