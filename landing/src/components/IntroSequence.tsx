import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { ASSETS } from "@/lib/constants";
import { EASE } from "@/lib/constants";

const RAY_ANGLES = [0, 30, 60, 120, 150, 210, 240, 300, 330];
const TOTAL_MS = 3600;

function rayPath(angleDeg: number, length = 60) {
  const rad = (angleDeg * Math.PI) / 180;
  const x2 = 50 + Math.cos(rad) * length;
  const y2 = 50 + Math.sin(rad) * length;
  return `M 50 50 L ${x2} ${y2}`;
}

function LogoFallback({ className }: { className?: string }) {
  return (
    <span className={`font-display font-black text-2xl ${className ?? ""}`}>
      <span className="text-teal">Med</span>
      <span className="text-[oklch(0.13_0.03_240)]">Band</span>
    </span>
  );
}

export function IntroSequence() {
  const reduced = useReducedMotion();
  const [hidden, setHidden] = useState(false);
  const [logoFailed, setLogoFailed] = useState(false);
  const duration = reduced ? 0.1 : TOTAL_MS / 1000;

  useEffect(() => {
    const t = setTimeout(() => setHidden(true), reduced ? 100 : TOTAL_MS);
    return () => clearTimeout(t);
  }, [reduced]);

  if (hidden) return null;

  return (
    <div
      className="fixed inset-0 z-[100] pointer-events-none"
      aria-hidden
    >
      <motion.div
        className="absolute inset-0 bg-[oklch(0.09_0.006_220)]"
        initial={{ opacity: 1 }}
        animate={{ opacity: reduced ? 0 : [1, 1, 0] }}
        transition={{
          duration,
          times: [0, 0.82, 1],
          ease: EASE,
        }}
      />

      <div className="absolute inset-0 flex items-center justify-center">
        {[1, 2, 3].map((n, i) => (
          <motion.div
            key={n}
            className="absolute rounded-full border border-[var(--teal)]"
            style={{
              width: 260 * n,
              height: 260 * n,
              borderColor: "color-mix(in oklch, var(--teal) 10%, transparent)",
            }}
            initial={{ opacity: 0, scale: 0.15 }}
            animate={{ opacity: [0, 0.55, 0], scale: [0.15, 1, 1.4] }}
            transition={{
              duration: reduced ? 0.1 : 2.4,
              delay: reduced ? 0 : [1.22, 1.34, 1.46][i],
              times: [0, 0.5, 1],
              ease: EASE,
            }}
          />
        ))}

        <svg
          className="absolute"
          viewBox="0 0 100 100"
          style={{ width: "min(80vw, 400px)", height: "min(80vw, 400px)" }}
        >
          {RAY_ANGLES.map((angle, i) => (
            <motion.path
              key={angle}
              d={rayPath(angle)}
              fill="none"
              stroke="var(--teal)"
              strokeOpacity={0.45}
              strokeWidth={0.12}
              strokeLinecap="round"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: [0, 1, 1], opacity: [0, 0.65, 0] }}
              transition={{
                duration: reduced ? 0.1 : 2,
                delay: reduced ? 0 : 1.2 + i * 0.05,
                times: [0, 0.7, 1],
                ease: EASE,
              }}
            />
          ))}
        </svg>

        <motion.div
          className="absolute"
          style={{ top: "50%", left: "50%" }}
          initial={{ x: "-50%", y: "-50%", scale: 1 }}
          animate={{
            top: reduced ? "24px" : ["50%", "50%", "50%", "24px"],
            left: reduced ? "24px" : ["50%", "50%", "50%", "24px"],
            x: reduced ? "0%" : ["-50%", "-50%", "-50%", "0%"],
            y: reduced ? "0%" : ["-50%", "-50%", "-50%", "0%"],
            scale: reduced ? 0.42 : [1, 1, 1, 0.42],
          }}
          transition={{
            duration,
            times: [0, 0.6, 0.82, 1],
            ease: EASE,
          }}
        >
          <motion.div
            className="absolute rounded-full bg-[var(--teal)]"
            style={{ left: 32, top: 32, transform: "translate(-50%, -50%)" }}
            initial={{ width: 8, height: 8, opacity: 1 }}
            animate={{
              width: reduced ? 0 : [8, 10, 64, 64],
              height: reduced ? 0 : [8, 10, 64, 64],
              opacity: reduced ? 0 : [1, 1, 1, 0],
            }}
            transition={{
              duration,
              times: [0, 0.18, 0.4, 1],
              ease: EASE,
            }}
          />

          <motion.div
            className="overflow-hidden"
            initial={{ width: 64, opacity: 0 }}
            animate={{
              width: reduced ? 268 : [64, 64, 64, 268, 268],
              opacity: reduced ? 1 : [0, 0, 1, 1, 1],
            }}
            transition={{
              duration,
              times: [0, 0.3, 0.42, 0.78, 1],
              ease: EASE,
            }}
            style={{ height: 64 }}
          >
            {logoFailed ? (
              <LogoFallback />
            ) : (
              <img
                src={ASSETS.logo}
                alt=""
                className="h-16 max-w-none"
                style={{ width: 268, height: 64 }}
                onError={() => setLogoFailed(true)}
              />
            )}
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}
