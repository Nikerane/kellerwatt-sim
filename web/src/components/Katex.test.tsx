import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Katex } from "./Katex";

describe("Katex", () => {
  it("renders tex to katex html without throwing", () => {
    const { container } = render(<Katex tex={"a = \\frac{b}{c}"} />);
    expect(container.querySelector(".katex")).toBeTruthy();
  });
  it("does not throw on a malformed expression", () => {
    expect(() => render(<Katex tex={"\\frac{"} />)).not.toThrow();
  });
});
