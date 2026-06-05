/** Cross-page navigation. All hrefs are relative (./) so links work on
 *  every deploy target (GitHub Pages subpath, local, HF Spaces). */
export function SiteNav({ current }: { current: "honesty" | "methodology" | "playground" }) {
  return (
    <nav className="kw-nav" aria-label="Primary">
      <a className="kw-nav__brand" href="https://kellerwatt.de">KellerWatt</a>
      <span className="kw-nav__links">
        <a aria-current={current === "honesty" ? "page" : undefined} href="./index.html">
          The number
        </a>
        <a aria-current={current === "methodology" ? "page" : undefined} href="./methodology.html">
          Methodology
        </a>
        <a aria-current={current === "playground" ? "page" : undefined} href="./playground.html">
          Playground
        </a>
      </span>
    </nav>
  );
}
