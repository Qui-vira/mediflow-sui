import { useEffect, useState } from "react";
import { m } from "framer-motion";
import { EASE } from "@/lib/constants";

type Variant = "hero" | "photographer" | "projects" | "marvels" | "marvelsBottom";

const LINES: Record<Variant, [number, number, number, number][]> = {
  hero: [
    [0, 0, 22, 100],
    [50, 0, 82, 100],
    [100, 0, 58, 100],
    [0, 35, 100, 80],
    [100, 10, 0, 70],
    [30, 0, 100, 55],
  ],
  photographer: [
    [22, 0, 14, 100],
    [58, 0, 48, 100],
    [82, 0, 86, 100],
    [0, 20, 100, 90],
    [100, 15, 0, 80],
  ],
  projects: [
    [14, 0, 28, 100],
    [48, 0, 64, 100],
    [86, 0, 92, 100],
    [0, 30, 100, 75],
    [100, 5, 0, 90],
  ],
  marvels: [
    [28, 0, 18, 100],
    [64, 0, 50, 100],
    [92, 0, 80, 100],
    [0, 15, 100, 85],
  ],
  marvelsBottom: [
    [10, 30, 45, 35],
    [55, 28, 92, 32],
    [8, 55, 40, 58],
    [60, 62, 90, 60],
    [20, 78, 80, 82],
  ],
};

interface Marker {
  lineIndex: number;
  t: number;
  label: string;
}

const MARKERS: Partial<Record<Variant, Marker[]>> = {
  hero: [
    { lineIndex: 1, t: 0.38, label: "MEDIFLOW-20250609-ADA001 INTAKE_COMPLETE" },
    { lineIndex: 3, t: 0.62, label: "MEDIFLOW-20250609-ROH002 CASE_ESCALATE" },
    { lineIndex: 5, t: 0.28, label: "MEDIFLOW-20250609-CHI003 CASE_CLEAR" },
  ],
  photographer: [
    { lineIndex: 0, t: 0.55, label: "VERIFICATION agent:nafdac_check passed" },
    { lineIndex: 3, t: 0.72, label: "RESOURCE agent:stock_confirmed 450units" },
  ],
  projects: [
    { lineIndex: 1, t: 0.41, label: "COORDINATOR room:MediFlow-ADA001 created" },
    { lineIndex: 4, t: 0.58, label: "INTAKE agent:structured_payload ready" },
    { lineIndex: 2, t: 0.83, label: "RESOURCE agent:RESOURCE_COMPLETE sent" },
  ],
};

interface LineFieldProps {
  variant?: Variant;
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

function useDesktopMarkers() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1025px)");
    const update = () => setShow(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  return show;
}

export function LineField({ variant = "hero" }: LineFieldProps) {
  const lines = LINES[variant];
  const markers = MARKERS[variant] ?? [];
  const strokeOpacity = variant === "marvelsBottom" ? 0.22 : 0.1;
  const showHeroMarkers = useDesktopMarkers();
  const isHero = variant === "hero";

  return (
    <svg
      className="absolute inset-0 pointer-events-none select-none"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      style={{ zIndex: 0 }}
      aria-hidden
    >
      {lines.map(([x1, y1, x2, y2], i) => {
        const mx = (x1 + x2) / 2;
        const my = (y1 + y2) / 2;
        return (
          <m.line
            key={i}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke="white"
            strokeWidth={0.08}
            strokeOpacity={strokeOpacity}
            initial={{ pathLength: 0, opacity: 0 }}
            whileInView={{ pathLength: 1, opacity: 1 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 1.4, delay: i * 0.12, ease: EASE }}
            style={{ transformOrigin: `${mx}% ${my}%` }}
          />
        );
      })}

      {markers.map((marker, i) => {
        if (isHero && !showHeroMarkers) return null;

        const line = lines[marker.lineIndex];
        if (!line) return null;
        const [x1, y1, x2, y2] = line;
        const px = lerp(x1, x2, marker.t);
        const py = lerp(y1, y2, marker.t);
        const words = marker.label.split(" ");
        const markerOpacity = isHero ? 0.15 : 1;
        const textOpacity = isHero ? 0.12 : 0.55;

        return (
          <m.g
            key={i}
            initial={{ opacity: 0, scale: 0 }}
            whileInView={{ opacity: markerOpacity, scale: 1 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.8, delay: 1.2 + i * 0.25, ease: EASE }}
            style={{ transformOrigin: `${px}% ${py}%` }}
          >
            <circle
              cx={px}
              cy={py}
              r={0.18}
              fill="white"
              fillOpacity={isHero ? 0.12 : 0.95}
            />
            <text
              x={px + 0.5}
              y={py - 0.6}
              fill="white"
              fillOpacity={textOpacity}
              fontSize={0.5}
              fontFamily="ui-monospace, monospace"
              letterSpacing="0.02em"
              style={{ opacity: isHero ? 0.12 : undefined }}
            >
              {words.map((word, wi) => (
                <tspan key={wi} x={px + 0.5} dy={wi === 0 ? 0 : "0.7em"}>
                  {word}
                </tspan>
              ))}
            </text>
          </m.g>
        );
      })}
    </svg>
  );
}
