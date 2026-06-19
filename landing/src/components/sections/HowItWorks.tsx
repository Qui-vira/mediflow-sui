import { m } from "framer-motion";
import { LineField } from "../LineField";
import { StarField } from "../StarField";
import { NoiseOverlay } from "../shared/landing-ui";
import { EASE, MATTE } from "@/lib/constants";
import {
  desktopStepIn,
  mobileCardIn,
  viewBlurIn,
  viewFadeIn,
} from "@/lib/motion";
import { AGENT_ROLES, STEPS, TIMELINE_NODES } from "@/lib/sectors";
import { useIsMobile } from "@/lib/useIsMobile";

export default function HowItWorks() {
  const isMobile = useIsMobile();
  const headingVariants = isMobile ? viewFadeIn : viewBlurIn;

  return (
    <section
      id="how-it-works"
      className={`${MATTE} relative px-6 md:px-12 py-32 overflow-hidden`}
    >
      <StarField count={200} />
      <LineField variant="photographer" />
      <NoiseOverlay />
      <div
        className="absolute -left-20 top-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full bg-teal/[0.03] blur-3xl pointer-events-none"
        style={{ zIndex: 1 }}
      />

      <div className="relative z-[2] max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-12 mb-20">
        <m.h2
          className="font-display font-medium text-5xl md:text-6xl uppercase leading-[0.95] text-white"
          variants={headingVariants}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-100px" }}
        >
          How MediFlow
          <br />
          Works
        </m.h2>
        <m.p
          className="text-white/55 text-[15px] max-w-md leading-relaxed self-end"
          variants={headingVariants}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-100px" }}
        >
          The working MVP is one complete Pharmacy workflow. AI agents
          coordinate each case through Band rooms — every handoff is visible,
          traceable, and tracked in Postgres — while a human reviewer keeps
          final approval.
        </m.p>
      </div>

      <div className="relative z-[2] max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-8">
        {STEPS.map((step) => (
          <m.div
            key={step.num}
            className="relative bg-card rounded-2xl p-8 border border-white/10 hover:border-teal/30 transition shadow-[0_40px_100px_-30px_rgba(0,0,0,0.8)]"
            variants={isMobile ? mobileCardIn : desktopStepIn}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-100px" }}
          >
            <span className="absolute top-4 right-6 font-display font-black text-6xl text-white/10">
              {step.num}
            </span>
            <step.icon
              className={`w-8 h-8 ${step.iconColor ?? "text-teal"} mb-4`}
            />
            <h3 className="font-display font-bold text-xl text-white">
              {step.title}
            </h3>
            <p className="text-white/55 text-sm mt-3 leading-relaxed">
              {step.body}
            </p>
          </m.div>
        ))}
      </div>

      <div className="relative z-[2] max-w-5xl mx-auto mt-16 overflow-x-auto px-4">
        <div className="flex items-start justify-between gap-0 min-w-[640px]">
          {TIMELINE_NODES.map((node, i) => (
            <div key={node} className="flex items-center flex-1 last:flex-none">
              <m.div
                className="flex flex-col items-center"
                initial={{ opacity: 0, scale: isMobile ? 1 : 0 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: i * 0.15, ease: EASE }}
              >
                <div className="w-3 h-3 bg-teal rounded-full" />
                <span className="text-xs text-white/50 text-center mt-2 w-24 leading-tight">
                  {node}
                </span>
              </m.div>
              {i < TIMELINE_NODES.length - 1 && (
                <div className="flex-1 h-px bg-white/20 mt-1.5 mx-1" />
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="relative z-[2] max-w-7xl mx-auto mt-28">
        <m.h3
          className="font-display font-bold text-3xl md:text-4xl text-white"
          variants={headingVariants}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-100px" }}
        >
          Agent roles
        </m.h3>
        <m.p
          className="text-white/55 text-[15px] max-w-md leading-relaxed mt-3"
          variants={headingVariants}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-100px" }}
        >
          Seven roles move each case forward. Only the human reviewer can
          approve or reject.
        </m.p>
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {AGENT_ROLES.map((role, i) => (
            <m.div
              key={role.name}
              className={`rounded-2xl border bg-card p-5 transition ${
                role.name === "Human Reviewer"
                  ? "border-green/40 hover:border-green/60"
                  : "border-white/10 hover:border-teal/30"
              }`}
              variants={isMobile ? mobileCardIn : desktopStepIn}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true, margin: "-80px" }}
              custom={i}
            >
              <h4
                className={`font-display font-bold text-base ${
                  role.name === "Human Reviewer" ? "text-green" : "text-white"
                }`}
              >
                {role.name}
              </h4>
              <p className="text-white/55 text-sm mt-2 leading-relaxed">
                {role.body}
              </p>
            </m.div>
          ))}
        </div>
      </div>
    </section>
  );
}
