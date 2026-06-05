import type { ReactNode } from "react";

type Size = "xl" | "lg" | "md";
type Tag = "h1" | "h2" | "h3" | "p";

/** The signature contrast couplet: two short declarative lines, the second cuts
    back at the first. Fraunces, tight tracking, sentence case. */
export function Couplet({
  first,
  second,
  as = "h2",
  size = "lg",
}: {
  first: ReactNode;
  second: ReactNode;
  as?: Tag;
  size?: Size;
}) {
  const Tag = as;
  return (
    <Tag className={`kw-couplet kw-couplet--${size}`}>
      <span className="kw-couplet__a">{first}</span>
      <span className="kw-couplet__b">{second}</span>
    </Tag>
  );
}
