import type { ElementType, ReactNode } from "react";

/** Bespoke editorial card: paper surface, 18px radius, hairline border, two-layer
    soft shadow. Not a generic library card. */
export function Card({
  children,
  as: Tag = "div",
  className = "",
}: {
  children: ReactNode;
  as?: ElementType;
  className?: string;
}) {
  return <Tag className={`kw-card ${className}`.trim()}>{children}</Tag>;
}
