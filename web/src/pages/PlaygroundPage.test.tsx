import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { PlaygroundPage } from "./PlaygroundPage";

// Mock fetch globally — the page calls the HF Space backend.
const mockFetch = vi.fn();
globalThis.fetch = mockFetch as any;

beforeEach(() => {
  mockFetch.mockReset();
  // Default: health check succeeds immediately
  mockFetch.mockResolvedValue({
    ok: true,
    json: async () => ({ status: "ok" }),
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("PlaygroundPage", () => {
  it("renders the hero couplet", () => {
    render(<PlaygroundPage />);
    expect(
      screen.getByRole("heading", { name: /Change the assumptions\./ }),
    ).toBeInTheDocument();
  });

  it("renders all six sliders", () => {
    render(<PlaygroundPage />);
    expect(screen.getByLabelText("Battery capacity")).toBeInTheDocument();
    expect(screen.getByLabelText("Power rating")).toBeInTheDocument();
    expect(screen.getByLabelText("Round-trip efficiency")).toBeInTheDocument();
    expect(screen.getByLabelText("Assumed spread")).toBeInTheDocument();
    expect(screen.getByLabelText("Daily cycle cap")).toBeInTheDocument();
    expect(screen.getByLabelText("Grid energy fee")).toBeInTheDocument();
  });

  it("renders the exemption toggle with both options", () => {
    render(<PlaygroundPage />);
    expect(
      screen.getByRole("button", { name: "Retained" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Lost" })).toBeInTheDocument();
  });

  it("shows default results on initial render (baked-in data)", () => {
    render(<PlaygroundPage />);
    // The default baked-in data should show a results table for the latest year
    expect(screen.getByText("Captured spread · 2025")).toBeInTheDocument();
  });

  it("renders cross-page nav with playground link", () => {
    render(<PlaygroundPage />);
    expect(screen.getByRole("link", { name: "Playground" })).toHaveAttribute(
      "href",
      "/playground.html",
    );
  });

  it("slider changes update value displays without crashing", () => {
    render(<PlaygroundPage />);
    // Since ENGINE_URL is empty, there's no fetch — just verify the DOM updates
    const slider = screen.getByLabelText(
      "Battery capacity",
    ) as HTMLInputElement;
    fireEvent.change(slider, { target: { value: "300" } });
    // Value display should update
    expect(screen.getByText("300 kWh")).toBeInTheDocument();
  });

  it("shows ready status when no engine URL is configured", () => {
    render(<PlaygroundPage />);
    // With ENGINE_URL empty, it should show Ready immediately
    expect(screen.getByText(/Ready/)).toBeInTheDocument();
  });
});
