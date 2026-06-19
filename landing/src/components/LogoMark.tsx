import type { CSSProperties } from "react";

const wordStyle = {
  fontFamily: "'Space Grotesk', system-ui, sans-serif",
  fontWeight: 700,
} as const;

export function LogoMark({ style }: { style?: CSSProperties }) {
  return (
    <span
      style={{
        display: "inline-block",
        whiteSpace: "nowrap",
        letterSpacing: "-0.02em",
        ...style,
      }}
      aria-label="MediFlow"
    >
      <span style={{ ...wordStyle, color: "#0E7C7B" }}>Med</span>
      <span style={{ ...wordStyle, color: "#FFFFFF" }}>Band</span>
    </span>
  );
}
