import { SiteNav } from "../components/SiteNav";
import { Eyebrow } from "../components/Eyebrow";
import { Couplet } from "../components/Couplet";

// Stub — sections (assumptions, formula catalog, per-year table, limitations) are
// filled in Task 4.
export function MethodologyPage() {
  return (
    <main className="kw-page">
      <SiteNav current="methodology" />
      <section className="kw-section kw-section--bone">
        <div className="kw-section__inner">
          <Eyebrow>How the number is computed</Eyebrow>
          <Couplet
            as="h1"
            size="lg"
            first="The conclusions are on the front page."
            second="Here are the workings."
          />
        </div>
      </section>
    </main>
  );
}
