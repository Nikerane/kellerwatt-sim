import { DataMono } from "./DataMono";

export interface SliderDef {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
  default: number;
  unit: string;
  /** Optional: format the value differently from the raw number (e.g. "90%" for 0.90). */
  formatValue?: (v: number) => string;
  /** Optional: a short plain-language hint shown under the slider. */
  hint?: string;
}

interface Props {
  slider: SliderDef;
  value: number;
  onChange: (key: string, value: number) => void;
  disabled: boolean;
}

export function PlaygroundSlider({ slider, value, onChange, disabled }: Props) {
  return (
    <label
      className="kw-slider"
      style={{ display: "flex", flexDirection: "column", gap: 6 }}
    >
      <span
        className="kw-slider__label"
        style={{ display: "flex", justifyContent: "space-between" }}
      >
        <span style={{ fontFamily: "var(--sans)", fontSize: "0.85rem", color: "var(--slate)" }}>
          {slider.label}
        </span>
        <DataMono tone="ember" size="sm">
          {slider.formatValue ? slider.formatValue(value) : `${value} ${slider.unit}`}
        </DataMono>
      </span>
      <input
        type="range"
        min={slider.min}
        max={slider.max}
        step={slider.step}
        value={value}
        onChange={(e) => onChange(slider.key, parseFloat(e.target.value))}
        disabled={disabled}
        className="kw-slider__input"
        aria-label={slider.label}
      />
      <span
        className="kw-slider__range-labels"
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "0.72rem",
          opacity: 0.5,
        }}
      >
        <span>{slider.formatValue ? slider.formatValue(slider.min) : `${slider.min}`}</span>
        <span>{slider.formatValue ? slider.formatValue(slider.max) : `${slider.max}`}</span>
      </span>
      {slider.hint && (
        <span
          className="kw-slider__hint"
          style={{
            fontFamily: "var(--sans)",
            fontSize: "0.72rem",
            opacity: 0.5,
            color: "var(--slate)",
          }}
        >
          {slider.hint}
        </span>
      )}
    </label>
  );
}
