import { m } from "framer-motion";
import {
  ArrowUpRight,
  Brain,
  FlaskConical,
  Heart,
  Pill,
  Shield,
  Siren,
  type LucideIcon,
} from "lucide-react";
import { LineField } from "../LineField";
import { StarField } from "../StarField";
import { NoiseOverlay } from "../shared/landing-ui";
import { LINKS, MATTE } from "@/lib/constants";
import {
  desktopCardIn,
  mobileCardIn,
  viewBlurIn,
  viewFadeIn,
  viewFadeUp,
} from "@/lib/motion";
import { useIsMobile } from "@/lib/useIsMobile";

type InstitutionCard = {
  name: string;
  sector: string;
  icon: LucideIcon;
  status: "Live MVP" | "Roadmap";
  note: string;
};

const INSTITUTION_CARDS: InstitutionCard[] = [
  {
    name: "Peaceway Pharmacy",
    sector: "Pharmacy",
    icon: Pill,
    status: "Live MVP",
    note: "Pilot institution for the live, production-verified Pharmacy workflow.",
  },
  {
    name: "Hospital Triage",
    sector: "Hospitals",
    icon: Heart,
    status: "Roadmap",
    note: "Example target sector for future expansion.",
  },
  {
    name: "Lab / Diagnostics",
    sector: "Diagnostics",
    icon: FlaskConical,
    status: "Roadmap",
    note: "Example target sector for future expansion.",
  },
  {
    name: "HMO / Insurance",
    sector: "Insurance",
    icon: Shield,
    status: "Roadmap",
    note: "Example target sector for future expansion.",
  },
  {
    name: "Mental Health",
    sector: "Wellness",
    icon: Brain,
    status: "Roadmap",
    note: "Example target sector for future expansion.",
  },
  {
    name: "Emergency Dispatch",
    sector: "Emergency",
    icon: Siren,
    status: "Roadmap",
    note: "Example target sector for future expansion.",
  },
];

export default function TrustedInstitutions() {
  const isMobile = useIsMobile();
  const headingVariants = isMobile ? viewFadeIn : viewBlurIn;

  return (
    <section
      id="institutions"
      className={`${MATTE} relative px-6 md:px-12 py-32 overflow-hidden`}
    >
      <StarField count={200} />
      <LineField variant="photographer" />
      <NoiseOverlay />
      <div
        className="absolute -right-20 top-1/3 w-[500px] h-[500px] rounded-full bg-teal/[0.03] blur-3xl pointer-events-none"
        style={{ zIndex: 1 }}
      />

      <div className="relative z-[2] max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-12 mb-20">
        <m.h2
          className="font-display font-black text-5xl md:text-6xl uppercase leading-[0.95]"
          variants={headingVariants}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-100px" }}
        >
          Built for Healthcare
          <br />
          Institutions
        </m.h2>
        <m.p
          className="text-white/55 text-[15px] max-w-md leading-relaxed self-end"
          variants={headingVariants}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-100px" }}
        >
          Proven first with Pharmacy. MediFlow's live MVP is proven through a
          Pharmacy workflow with Peaceway Pharmacy. The same human-in-the-loop
          architecture can later expand to hospitals, labs, HMOs, mental health
          teams, and emergency dispatch partners.
        </m.p>
      </div>

      <div className="relative z-[2] max-w-7xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
        {INSTITUTION_CARDS.map((card, i) => {
          const isLive = card.status === "Live MVP";
          return (
            <m.div
              key={card.name}
              className={`rounded-2xl p-6 border bg-[oklch(0.11_0.006_220)] transition-all duration-300 ${
                isLive
                  ? "border-green/40 hover:border-green/60"
                  : "border-white/10 hover:border-amber/40"
              }`}
              variants={isMobile ? mobileCardIn : desktopCardIn(i * 0.08)}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true, margin: "-80px" }}
            >
              <div className="flex items-start gap-4">
                <div
                  className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${
                    isLive ? "bg-green/15" : "bg-white/[0.04]"
                  }`}
                >
                  <card.icon
                    className={`w-6 h-6 ${isLive ? "text-green" : "text-teal"}`}
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="font-display font-bold text-lg text-white truncate">
                    {card.name}
                  </h3>
                  <p className="text-white/50 text-sm mt-0.5">{card.sector}</p>
                </div>
              </div>

              <p className="text-white/55 text-sm mt-4 leading-relaxed">
                {card.note}
              </p>

              {isLive ? (
                <span className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-green/20 border border-green/30 px-2 py-0.5 text-xs text-green">
                  <span className="w-1.5 h-1.5 rounded-full bg-green" />
                  Live MVP
                </span>
              ) : (
                <span className="mt-4 inline-flex items-center rounded-full bg-amber/15 border border-amber/30 px-2 py-0.5 text-xs text-amber">
                  Roadmap
                </span>
              )}
            </m.div>
          );
        })}
      </div>

      <m.div
        className="relative z-[2] max-w-7xl mx-auto mt-16 text-center"
        variants={isMobile ? viewFadeIn : viewFadeUp}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, margin: "-100px" }}
      >
        <a
          href={LINKS.register}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-full bg-teal text-white px-8 py-3 font-medium hover:bg-teal/80 transition"
        >
          Register Your Institution
          <ArrowUpRight className="w-4 h-4" />
        </a>
      </m.div>
    </section>
  );
}
