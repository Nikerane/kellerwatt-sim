import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { HonestyPage } from "./HonestyPage";

describe("HonestyPage", () => {
  it("still leads with the hero couplet after the page split", () => {
    render(<HonestyPage />);
    expect(
      screen.getByRole("heading", { name: /We assumed €80 a megawatt-hour\./ }),
    ).toBeInTheDocument();
  });

  it("renders the cross-page nav with both destinations", () => {
    render(<HonestyPage />);
    expect(screen.getByRole("link", { name: "Methodology" })).toHaveAttribute(
      "href",
      "/methodology.html",
    );
  });
});
