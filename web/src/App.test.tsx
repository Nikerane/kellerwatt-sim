import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { App } from "./App";

describe("App (the honesty page)", () => {
  it("leads with the honest hero couplet", () => {
    render(<App />);
    expect(
      screen.getByRole("heading", { name: /We assumed €80 a megawatt-hour\./ }),
    ).toBeInTheDocument();
    expect(screen.getByText("Real prices never got there.")).toBeInTheDocument();
  });

  it("names the two open diligence items", () => {
    render(<App />);
    expect(screen.getByText("Aggregator term sheet")).toBeInTheDocument();
    expect(screen.getByText("§118(6) EnWG legal memo")).toBeInTheDocument();
  });

  it("shows provenance with the solver", () => {
    render(<App />);
    expect(screen.getByText(/HiGHS/)).toBeInTheDocument();
  });
});
