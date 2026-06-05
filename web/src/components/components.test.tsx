import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Eyebrow } from "./Eyebrow";
import { Couplet } from "./Couplet";
import { DataMono } from "./DataMono";
import { Card } from "./Card";
import { CaseTable } from "./CaseTable";
import { SpreadChart } from "./SpreadChart";

describe("primitives", () => {
  it("Eyebrow renders text and the ember signal modifier", () => {
    const { container } = render(<Eyebrow ember>Validated</Eyebrow>);
    const el = container.querySelector(".kw-eyebrow");
    expect(el).toHaveTextContent("Validated");
    expect(el).toHaveClass("kw-eyebrow--ember");
  });

  it("Couplet renders both lines, second cuts back", () => {
    render(<Couplet first="Cheap power exists." second="Most homes can't reach it." />);
    expect(screen.getByText("Cheap power exists.")).toBeInTheDocument();
    expect(screen.getByText("Most homes can't reach it.")).toBeInTheDocument();
  });

  it("DataMono carries the tabular-mono class and tone", () => {
    const { container } = render(<DataMono tone="ember">€77.3</DataMono>);
    const el = container.querySelector(".kw-mono");
    expect(el).toHaveClass("kw-mono--ember");
    expect(el).toHaveTextContent("€77.3");
  });

  it("Card is a bespoke surface", () => {
    const { container } = render(<Card>body</Card>);
    expect(container.querySelector(".kw-card")).toHaveTextContent("body");
  });
});

describe("CaseTable", () => {
  it("renders the four cases with the validated best-case as the signal", () => {
    render(<CaseTable year={2025} />);
    expect(screen.getByText("Assumed")).toBeInTheDocument();
    expect(screen.getByText("Best-case")).toBeInTheDocument();
    expect(screen.getByText("Realistic")).toBeInTheDocument();
    expect(screen.getByText("Conservative")).toBeInTheDocument();
    // the validated 2025 best-case spread appears
    expect(screen.getByText("€77.3")).toBeInTheDocument();
    // exactly one "validated" status tag (the best-case column)
    expect(screen.getAllByText("validated")).toHaveLength(1);
  });
});

describe("SpreadChart", () => {
  it("renders an accessible SVG with the ceiling and assumed values", () => {
    const { container } = render(<SpreadChart />);
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("role", "img");
    expect(svg?.getAttribute("aria-label")).toMatch(/best €77.3/);
    expect(svg?.getAttribute("aria-label")).toMatch(/€80/);
    // bracket + best + real lines at least.
    expect(container.querySelectorAll("path").length).toBeGreaterThanOrEqual(3);
  });
});
