import { useEffect, useRef } from "react";

interface Star {
  x: number;
  y: number;
  r: number;
  opacity: number;
  twinkleSpeed: number;
  twinkleOffset: number;
  color: string;
  radiusOffset?: number;
}

interface StarFieldProps {
  count?: number;
  className?: string;
  ring?: boolean;
  ringCount?: number;
  ringRadiusFactor?: number;
  ringBandWidth?: number;
}

function rand(min: number, max: number) {
  return min + Math.random() * (max - min);
}

function gaussian(mean: number, std: number) {
  const u1 = Math.random();
  const u2 = Math.random();
  const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  return mean + z * std;
}

function pickStarColor(): string {
  const roll = Math.random();
  if (roll < 0.7) return "rgba(255,255,255,1)";
  if (roll < 0.9) return "rgba(14,124,123,0.55)";
  return "rgba(244,162,97,0.35)";
}

function pickRadius(): number {
  const roll = Math.random();
  if (roll < 0.65) return rand(0.25, 0.5);
  if (roll < 0.92) return rand(0.5, 0.8);
  return rand(0.8, 1.3);
}

function pickRingRadius(): number {
  const roll = Math.random();
  if (roll < 0.7) return rand(0.15, 0.3);
  if (roll < 0.93) return rand(0.3, 0.5);
  return rand(0.5, 0.7);
}

export function StarField({
  count = 600,
  className = "absolute inset-0 pointer-events-none",
  ring = false,
  ringCount = 240,
  ringRadiusFactor = 0.36,
  ringBandWidth = 52,
}: StarFieldProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const starsRef = useRef<Star[]>([]);
  const ringStarsRef = useRef<Star[]>([]);
  const ringRRef = useRef(0);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const buildStars = (w: number, h: number) => {
      const bg: Star[] = [];
      for (let i = 0; i < count; i++) {
        bg.push({
          x: Math.random() * w,
          y: Math.random() * h,
          r: pickRadius(),
          opacity: rand(0.2, 0.95),
          twinkleSpeed: rand(0.4, 1.6),
          twinkleOffset: rand(0, Math.PI * 2),
          color: pickStarColor(),
        });
      }
      starsRef.current = bg;

      const cx = w / 2;
      const cy = h / 2;
      const ringR = Math.min(w, h) * ringRadiusFactor;
      ringRRef.current = ringR;
      const half = ringBandWidth / 2;

      const rs: Star[] = [];
      if (ring) {
        for (let i = 0; i < ringCount * 2; i++) {
          const angle = Math.random() * Math.PI * 2;
          const offset = gaussian(0, half * 0.65);
          const dist = ringR + offset;
          rs.push({
            x: cx + Math.cos(angle) * dist,
            y: cy + Math.sin(angle) * dist,
            r: pickRingRadius(),
            opacity: rand(0.25, 0.8),
            twinkleSpeed: rand(0.3, 1.3),
            twinkleOffset: rand(0, Math.PI * 2),
            color: pickStarColor(),
            radiusOffset: offset,
          });
        }
      }
      ringStarsRef.current = rs;
    };

    const resize = () => {
      const parent = canvas.parentElement;
      if (!parent) return;
      const dpr = window.devicePixelRatio || 1;
      const w = parent.clientWidth;
      const h = parent.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      buildStars(w, h);
    };

    const ro = new ResizeObserver(resize);
    if (canvas.parentElement) ro.observe(canvas.parentElement);
    resize();

    const drawStar = (star: Star, t: number, bandFactor = 1) => {
      const twinkle =
        0.55 +
        0.45 *
          (Math.sin(t * star.twinkleSpeed + star.twinkleOffset) * 0.5 + 0.5);
      const alpha = star.opacity * twinkle * bandFactor;

      if (star.r > 1.0) {
        const glowR = star.r * (bandFactor < 1 ? 5 : 4);
        const grad = ctx.createRadialGradient(
          star.x,
          star.y,
          0,
          star.x,
          star.y,
          glowR,
        );
        grad.addColorStop(0, star.color.replace(/[\d.]+\)$/, `${alpha * 0.4})`));
        grad.addColorStop(1, "transparent");
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(star.x, star.y, glowR, 0, Math.PI * 2);
        ctx.fill();
      }

      ctx.globalAlpha = alpha;
      ctx.fillStyle = star.color;
      ctx.beginPath();
      ctx.arc(star.x, star.y, star.r, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
    };

    const draw = (t: number) => {
      const w = canvas.width / (window.devicePixelRatio || 1);
      const h = canvas.height / (window.devicePixelRatio || 1);
      ctx.clearRect(0, 0, w, h);

      if (ring) {
        const ringR = ringRRef.current;
        const cx = w / 2;
        const cy = h / 2;
        const grad = ctx.createRadialGradient(cx, cy, ringR - ringBandWidth * 4, cx, cy, ringR + ringBandWidth * 4);
        grad.addColorStop(0, "rgba(14,124,123,0)");
        grad.addColorStop(0.42, "rgba(14,124,123,0.022)");
        grad.addColorStop(0.5, "rgba(14,124,123,0.038)");
        grad.addColorStop(0.58, "rgba(14,124,123,0.022)");
        grad.addColorStop(1, "transparent");
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, w, h);

        for (const star of ringStarsRef.current) {
          const bandFactor = Math.max(
            0.15,
            1 - Math.abs(star.radiusOffset ?? 0) / (ringBandWidth * 0.65),
          );
          drawStar(star, t, bandFactor);
        }
      }

      for (const star of starsRef.current) {
        drawStar(star, t);
      }

      rafRef.current = requestAnimationFrame(() => draw(performance.now() / 1000));
    };

    rafRef.current = requestAnimationFrame(() => draw(performance.now() / 1000));

    return () => {
      ro.disconnect();
      cancelAnimationFrame(rafRef.current);
    };
  }, [count, ring, ringCount, ringRadiusFactor, ringBandWidth]);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{ zIndex: 0 }}
      aria-hidden
    />
  );
}
