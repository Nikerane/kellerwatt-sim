import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DailyDispatchChart } from "./DailyDispatchChart";
import type { DayDetailResponse } from "../data/playground";

const mockData: DayDetailResponse = {
  date: "2025-03-14",
  num_intervals: 96,
  dt_h: 0.25,
  prices: Array.from({ length: 96 }, (_, i) => 30 + i * 0.5),
  best_date: "2025-04-17",
  worst_date: "2025-01-01",
  available_dates: ["2025-01-01", "2025-03-14", "2025-04-17"],
  ceiling: {
    gross_eur: 23.45,
    mwh_discharged: 0.18,
    mwh_charged: 0.19,
    avg_buy_price: 38.2,
    avg_sell_price: 78.9,
    charge_kw: [0, 50, 50, 0],
    discharge_kw: [50, 0, 0, 0],
    soc_kwh: [20, 63, 106, 86],
  },
  causal: {
    gross_eur: 18.12,
    mwh_discharged: 0.15,
    mwh_charged: 0.16,
    avg_buy_price: 40.1,
    avg_sell_price: 75.3,
    charge_kw: [0, 50, 0, 0],
    discharge_kw: [0, 0, 0, 0],
    soc_kwh: [20, 63, 63, 63],
  },
};

describe("DailyDispatchChart", () => {
  it("renders ceiling strategy title", () => {
    render(<DailyDispatchChart data={mockData} strategy="ceiling" />);
    expect(
      screen.getByText("Best-case (perfect info)"),
    ).toBeInTheDocument();
  });

  it("renders causal strategy title", () => {
    render(<DailyDispatchChart data={mockData} strategy="causal" />);
    expect(
      screen.getByText("Realistic (actual strategy)"),
    ).toBeInTheDocument();
  });

  it("shows the net margin in the summary", () => {
    render(<DailyDispatchChart data={mockData} strategy="ceiling" />);
    expect(screen.getByText(/€23\.45/)).toBeInTheDocument();
  });

  it("shows avg buy and sell prices", () => {
    render(<DailyDispatchChart data={mockData} strategy="ceiling" />);
    expect(screen.getByText(/€38\.2/)).toBeInTheDocument();
    expect(screen.getByText(/€78\.9/)).toBeInTheDocument();
  });

  it("renders an SVG chart with aria-label", () => {
    render(<DailyDispatchChart data={mockData} strategy="ceiling" />);
    const svg = screen.getByRole("img");
    expect(svg).toBeInTheDocument();
    expect(svg.getAttribute("aria-label")).toContain("Best-case");
  });

  it("shows the legend with charging/discharging/price", () => {
    render(<DailyDispatchChart data={mockData} strategy="ceiling" />);
    expect(screen.getByText("Charging")).toBeInTheDocument();
    expect(screen.getByText("Discharging")).toBeInTheDocument();
    expect(screen.getByText("Price")).toBeInTheDocument();
  });

  it("handles empty arrays gracefully", () => {
    const emptyData: DayDetailResponse = {
      ...mockData,
      num_intervals: 0,
      prices: [],
      ceiling: {
        ...mockData.ceiling,
        charge_kw: [],
        discharge_kw: [],
        soc_kwh: [],
      },
    };
    render(<DailyDispatchChart data={emptyData} strategy="ceiling" />);
    expect(screen.getByRole("img")).toBeInTheDocument();
  });
});
