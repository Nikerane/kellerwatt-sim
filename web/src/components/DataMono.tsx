import type { ReactNode } from "react";

type Tone = "neutral" | "ember" | "clay" | "muted";
type Size = "xl" | "lg" | "md" | "sm";

/** Every figure on the page. JetBrains Mono, tabular-nums. Colour follows the
    data role contract: ember = active/revenue, clay = cost/negative, neutral =
    label, muted = secondary. */
export function DataMono({
  children,
  tone = "neutral",
  size = "md",
  label,
}: {
  children: ReactNode;
  tone?: Tone;
  size?: Size;
  label?: string;
}) {
  return (
    <span className={`kw-mono kw-mono--${tone} kw-mono--${size}`} aria-label={label}>
      {children}
    </span>
  );
}
