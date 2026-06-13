import type { Variants } from "framer-motion";
import { EASE, INTRO_DELAY } from "./constants";

export const blurIn: Variants = {
  hidden: { opacity: 0, y: 24, filter: "blur(14px)" },
  show: (i = 0) => ({
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: 1.1, delay: INTRO_DELAY + i * 0.08, ease: EASE },
  }),
};

export const photoIn: Variants = {
  hidden: { opacity: 0, scale: 0.92, filter: "blur(12px)" },
  show: (i = 0) => ({
    opacity: 1,
    scale: 1,
    filter: "blur(0px)",
    transition: {
      duration: 1.2,
      delay: INTRO_DELAY + 0.1 + i * 0.1,
      ease: EASE,
    },
  }),
};

export const viewBlurIn = {
  hidden: { opacity: 0, y: 24, filter: "blur(14px)" },
  show: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration: 1.1, ease: EASE },
  },
};

export const viewFadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: (delay = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 1, delay, ease: EASE },
  }),
};
