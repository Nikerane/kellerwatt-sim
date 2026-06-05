import type { ReactNode } from "react";

/** Uppercase, mono, +0.22em tracked. Short — never wraps. Hierarchy from case,
    not colour (DESIGN.md). `ember` reserves the one signal per screen. */
export function Eyebrow({
  children,
  ember = false,
  className = "",
}: {
  children: ReactNode;
  ember?: boolean;
  className?: string;
}) {
  return (
    <span className={`kw-eyebrow ${ember ? "kw-eyebrow--ember" : ""} ${className}`.trim()}>
      {children}
    </span>
  );
}
