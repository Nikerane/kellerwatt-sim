/** Cross-page navigation between the honesty page and the methodology page. */
export function SiteNav({ current }: { current: "honesty" | "methodology" }) {
  return (
    <nav className="kw-nav" aria-label="Primary">
      <a className="kw-nav__brand" href="/index.html">KellerWatt</a>
      <span className="kw-nav__links">
        <a aria-current={current === "honesty" ? "page" : undefined} href="/index.html">
          The number
        </a>
        <a aria-current={current === "methodology" ? "page" : undefined} href="/methodology.html">
          Methodology
        </a>
      </span>
    </nav>
  );
}
