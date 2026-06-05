/** Cross-page navigation between the honesty page and the methodology page.
 *  All hrefs are relative (./) so links work on GitHub Pages subpath deploys. */
export function SiteNav({ current }: { current: "honesty" | "methodology" | "playground" }) {
  return (
    <nav className="kw-nav" aria-label="Primary">
      <a className="kw-nav__brand" href="https://nikerane.github.io/kellerwatt/index.html">KellerWatt</a>
      <span className="kw-nav__links">
        <a aria-current={current === "honesty" ? "page" : undefined} href="https://nikerane.github.io/kellerwatt-sim/index.html">
          The number
        </a>
        <a aria-current={current === "methodology" ? "page" : undefined} href="https://nikerane.github.io/kellerwatt-sim/methodology.html">
          Methodology
        </a>
        <a aria-current={current === "playground" ? "page" : undefined} href="https://nikerane.github.io/kellerwatt-sim/playground.html">
          Playground
        </a>
      </span>
    </nav>
  );
}
