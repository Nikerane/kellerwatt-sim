import katex from "katex";
import "katex/dist/katex.min.css";

/** Render a TeX string to KaTeX HTML. Self-hosted (GDPR-friendly); never throws on
    a bad expression (renders the source in red instead). */
export function Katex({ tex, display = false }: { tex: string; display?: boolean }) {
  const html = katex.renderToString(tex, { throwOnError: false, displayMode: display });
  return <span className="kw-katex" dangerouslySetInnerHTML={{ __html: html }} />;
}
