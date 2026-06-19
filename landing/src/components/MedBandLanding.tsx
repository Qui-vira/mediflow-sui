import { useEffect, useState, type CSSProperties } from "react";
import { LazyMotion, domAnimation, m, useReducedMotion } from "framer-motion";
import {
  ArrowUpRight,
  CheckCircle2,
  ChevronRight,
  Github,
  Menu,
  Pill,
  ShieldCheck,
  Siren,
  X,
} from "lucide-react";
import { lazy, Suspense } from "react";
import { IntroSequence } from "./IntroSequence";
import { LineField } from "./LineField";
import { StarField } from "./StarField";
import { SafeImage, Logo, NoiseOverlay } from "./shared/landing-ui";
import { SectionFallback, ViewportSection } from "./ViewportSection";
import { ASSETS, EASE, INTRO_DELAY, LINKS, MATTE } from "@/lib/constants";
import { blurIn, photoIn } from "@/lib/motion";

const HowItWorks = lazy(() => import("./sections/HowItWorks"));
const SixSectors = lazy(() => import("./sections/SixSectors"));
const TrustedInstitutions = lazy(() => import("./sections/TrustedInstitutions"));
const BandIntegration = lazy(() => import("./sections/BandIntegration"));
const Footer = lazy(() => import("./sections/Footer"));

function TopBar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const scrollTo = (id: string) => {
    setOpen(false);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  const navLinks = [
    { label: "How it Works", action: () => scrollTo("how-it-works") },
    { label: "Proof", action: () => scrollTo("proof") },
    { label: "MVP Scope", action: () => scrollTo("sectors") },
    { label: "GitHub", href: LINKS.github },
  ];

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 isolate border-b transition-all duration-300 ${
        scrolled
          ? "border-white/10 bg-black/70 backdrop-blur-md"
          : "border-white/5 bg-black/55 backdrop-blur-md"
      }`}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 sm:px-6 md:px-10">
        <m.a
          href="#"
          className="flex shrink-0 items-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: INTRO_DELAY - 0.2, ease: EASE }}
        >
          <Logo />
        </m.a>

        <m.nav
          className="hidden min-w-0 flex-1 items-center justify-center gap-0.5 lg:flex"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: INTRO_DELAY, ease: EASE }}
        >
          {navLinks.map((link) =>
            link.href ? (
              <a
                key={link.label}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="whitespace-nowrap px-3 py-2 text-sm text-white/60 transition hover:text-white xl:px-4"
              >
                {link.label}
              </a>
            ) : (
              <button
                key={link.label}
                type="button"
                onClick={link.action}
                className="whitespace-nowrap px-3 py-2 text-sm text-white/60 transition hover:text-white xl:px-4"
              >
                {link.label}
              </button>
            ),
          )}
        </m.nav>

        <m.div
          className="ml-auto flex shrink-0 items-center gap-2 sm:gap-3"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: INTRO_DELAY, ease: EASE }}
        >
          <a
            href={LINKS.register}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden items-center whitespace-nowrap rounded-full border border-teal/40 px-3 py-1.5 text-sm text-teal transition hover:bg-teal/10 sm:inline-flex"
          >
            For Institutions
          </a>
          <a
            href={LINKS.live}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center whitespace-nowrap rounded-full bg-teal px-3.5 py-2 text-sm text-white transition hover:bg-teal/80 sm:px-4"
          >
            Submit a Case
          </a>
          <button
            type="button"
            className="inline-flex p-2 text-white/80 transition hover:text-white lg:hidden"
            onClick={() => setOpen(!open)}
            aria-label={open ? "Close menu" : "Open menu"}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </m.div>
      </div>

      {open && (
        <div className="mx-4 mb-3 overflow-hidden rounded-xl border border-white/10 bg-black/90 backdrop-blur-md sm:mx-6 md:mx-10 lg:hidden">
          <a
            href={LINKS.register}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center justify-between px-4 py-3 text-sm text-teal hover:bg-teal/10 transition"
            onClick={() => setOpen(false)}
          >
            For Institutions
            <ArrowUpRight className="w-4 h-4 opacity-40 group-hover:opacity-100 transition" />
          </a>
          <a
            href={LINKS.live}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center justify-between px-4 py-3 text-sm text-white/80 hover:text-white hover:bg-white/[0.06] transition"
            onClick={() => setOpen(false)}
          >
            Submit a Case
            <ArrowUpRight className="w-4 h-4 opacity-40 group-hover:opacity-100 transition" />
          </a>
          {navLinks.map((link) =>
            link.href ? (
              <a
                key={link.label}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="group flex items-center justify-between px-4 py-3 text-sm text-white/80 hover:text-white hover:bg-white/[0.06] transition"
                onClick={() => setOpen(false)}
              >
                {link.label}
                <ArrowUpRight className="w-4 h-4 opacity-40 group-hover:opacity-100 transition" />
              </a>
            ) : (
              <button
                key={link.label}
                type="button"
                onClick={link.action}
                className="w-full group flex items-center justify-between px-4 py-3 text-sm text-white/80 hover:text-white hover:bg-white/[0.06] transition text-left"
              >
                {link.label}
                <ChevronRight className="w-4 h-4 opacity-40" />
              </button>
            ),
          )}
        </div>
      )}
    </header>
  );
}

const HERO_CARDS = [
  {
    src: ASSETS.bandRoom,
    alt: "Band room agents",
    position: "top-[46%] right-[3%]",
    size: "w-[280px] aspect-[16/10]",
    depth: 22,
    badge: "band" as const,
  },
  {
    src: ASSETS.form,
    alt: "Patient form",
    position: "top-[18%] left-[2%]",
    size: "w-[200px] aspect-[4/3]",
    depth: 18,
  },
  {
    src: ASSETS.dashboard,
    alt: "Band approval room",
    position: "bottom-[8%] right-[4%]",
    size: "w-[260px] aspect-[16/10]",
    depth: 26,
    badge: "live" as const,
  },
  {
    src: ASSETS.sectorPharmacy,
    alt: "Pharmacy sector",
    position: "top-[22%] left-[5%]",
    size: "w-[140px] aspect-square",
    depth: 20,
    fallbackIcon: Pill,
  },
  {
    src: ASSETS.sectorEmergency,
    alt: "Emergency dispatch",
    position: "bottom-[10%] left-[8%]",
    size: "w-[160px] aspect-square",
    depth: 24,
    fallbackIcon: Siren,
  },
];

function HeroSection() {
  const reduced = useReducedMotion();
  const [vars, setVars] = useState({ mx: 0, my: 0 });

  useEffect(() => {
    if (reduced) return;
    if (window.innerWidth < 768) return;
    const onMove = (e: MouseEvent) => {
      if (window.innerWidth < 768) return;
      const mx = e.clientX / window.innerWidth - 0.5;
      const my = e.clientY / window.innerHeight - 0.5;
      setVars({ mx, my });
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => window.removeEventListener("mousemove", onMove);
  }, [reduced]);

  const style = {
    "--mx": vars.mx,
    "--my": vars.my,
  } as CSSProperties;

  return (
    <section
      className={`${MATTE} relative min-h-[110vh] overflow-hidden pb-24 pt-28 md:pt-32`}
      style={style}
    >
      <StarField count={300} />
      <LineField variant="hero" />
      <NoiseOverlay />
      <div
        className="absolute -top-40 left-1/2 -translate-x-1/2 w-[800px] h-[800px] rounded-full bg-teal/[0.04] blur-3xl pointer-events-none"
        style={{ zIndex: 1 }}
      />
      {[0, 1].map((i) => (
        <div
          key={i}
          className="absolute top-[8%] left-1/2 w-[600px] h-[600px] rounded-full pointer-events-none opacity-30"
          style={{
            transform: `translateX(${i === 0 ? "-78%" : "-22%"})`,
            background:
              "radial-gradient(circle, transparent 60%, color-mix(in oklch, var(--teal) 25%, transparent) 61%, transparent 62%)",
            zIndex: 0,
          }}
          aria-hidden
        />
      ))}

      {HERO_CARDS.map((card, i) => (
        <m.div
          key={card.alt}
          className={`absolute z-[5] hidden lg:block ${card.position} ${card.size} group max-w-[min(280px,22vw)]`}
          variants={photoIn}
          initial="hidden"
          animate="show"
          custom={i}
          style={{
            transform: reduced
              ? undefined
              : `translate3d(calc(var(--mx) * ${card.depth}px), calc(var(--my) * ${card.depth}px), 0)`,
            transition: "transform 0.4s cubic-bezier(0.22, 1, 0.36, 1)",
          }}
        >
          <div className="relative w-full h-full overflow-hidden shadow-[0_30px_80px_-30px_rgba(0,0,0,0.9)] ring-1 ring-white/10">
            <SafeImage
              src={card.src}
              alt={card.alt}
              className="w-full h-full object-cover transition-transform duration-[1200ms] group-hover:scale-105"
              fallbackIcon={card.fallbackIcon}
            />
            {card.badge === "band" && (
              <span className="absolute bottom-2 right-2 h-6 px-2 rounded-md bg-teal text-white/90 text-xs font-medium flex items-center">
                band
              </span>
            )}
            {card.badge === "live" && (
              <span className="absolute bottom-2 right-2 h-6 px-2 rounded-md bg-green/80 text-white/90 text-xs font-medium flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                live
              </span>
            )}
          </div>
        </m.div>
      ))}

      <div className="relative z-10 grid place-items-center min-h-[60vh] px-6 md:px-8 text-center max-w-4xl mx-auto">
        <m.div
          className="inline-flex items-center gap-2 rounded-full border border-teal/30 bg-teal/10 px-3 py-1 text-xs text-teal uppercase tracking-widest mb-8"
          initial={{ opacity: 0, y: 20, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.8, delay: INTRO_DELAY, ease: EASE }}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-teal" />
          Band of Agents Hackathon 2026 · Track 3
        </m.div>

        <m.h1
          className="font-display font-black text-6xl md:text-7xl lg:text-8xl xl:text-[110px] leading-[0.95] tracking-tight"
          variants={blurIn}
          initial="hidden"
          animate="show"
          custom={1}
        >
          Medi<span className="text-teal">Flow</span>
        </m.h1>

        <m.p
          className="mt-6 font-display text-xl md:text-2xl text-white/85 max-w-2xl mx-auto leading-snug"
          variants={blurIn}
          initial="hidden"
          animate="show"
          custom={2}
        >
          Getting people to the right care, faster.
        </m.p>

        <m.p
          className="mt-6 text-white/55 text-base md:text-lg leading-relaxed max-w-xl mx-auto"
          variants={blurIn}
          initial="hidden"
          animate="show"
          custom={3}
        >
          AI agents coordinate intake, verification, resource checks, and case
          preparation, while final approval stays with a human reviewer.
        </m.p>

        <m.div
          className="mt-10 flex items-center gap-4 justify-center flex-wrap"
          variants={blurIn}
          initial="hidden"
          animate="show"
          custom={4}
        >
          <a
            href={LINKS.live}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-full bg-teal text-white px-8 py-3 font-medium hover:bg-teal/80 transition"
          >
            Open Live Demo
            <ArrowUpRight className="w-4 h-4" />
          </a>
          <a
            href={LINKS.github}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-full border border-white/20 text-white/70 px-8 py-3 hover:bg-white/5 transition"
          >
            View GitHub
            <Github className="w-4 h-4" />
          </a>
        </m.div>
      </div>

      <div className="relative z-10 mt-20 flex gap-12 justify-center flex-wrap px-6">
        {[
          { num: "1", label: "Live Pharmacy Workflow" },
          { num: "7", label: "Coordinated Roles" },
          { num: "100%", label: "Human Approval" },
        ].map((stat, i) => (
          <m.div
            key={stat.label}
            className="text-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.8,
              delay: INTRO_DELAY + 0.4 + i * 0.1,
              ease: EASE,
            }}
          >
            <div className="font-display font-black text-4xl text-teal">
              {stat.num}
            </div>
            <div className="text-white/50 text-sm mt-1">{stat.label}</div>
          </m.div>
        ))}
      </div>
    </section>
  );
}

function MobileFloatingCTA() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () =>
      setVisible(window.scrollY > window.innerHeight * 0.85);
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (!visible) return null;

  return (
    <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 px-4 pb-4 pointer-events-none">
      <div className="pointer-events-auto flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-black/90 backdrop-blur-md px-4 py-3 shadow-[0_-8px_40px_-12px_rgba(0,0,0,0.8)]">
        <p className="text-sm text-white/80 leading-snug">
          Is your institution on MediFlow?
        </p>
        <a
          href={LINKS.register}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 rounded-full bg-teal text-white px-4 py-2 text-sm font-medium hover:bg-teal/80 transition"
        >
          Register Now
        </a>
      </div>
    </div>
  );
}

const PROOF_ROWS = [
  { label: "Case ID", value: "MEDIFLOW-WEB-989E388C" },
  { label: "Sector", value: "Pharmacy" },
  { label: "Institution", value: "Peaceway Pharmacy (PHM001)" },
  { label: "Patient", value: "Band Human Approval Participant Test" },
  { label: "Issue", value: "BODY PAINS" },
  { label: "Request", value: "PARACETAMOL" },
];

function ProofSection() {
  return (
    <section
      id="proof"
      className={`${MATTE} relative px-6 md:px-12 py-32 overflow-hidden`}
    >
      <NoiseOverlay />
      <div
        className="absolute -right-20 top-1/3 w-[500px] h-[500px] rounded-full bg-green/[0.04] blur-3xl pointer-events-none"
        style={{ zIndex: 1 }}
      />
      <m.div
        className="relative z-[2] max-w-5xl mx-auto"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.7, ease: EASE }}
      >
        <span className="inline-flex items-center gap-2 rounded-full border border-green/30 bg-green/10 px-3 py-1 text-xs uppercase tracking-widest text-green">
          <CheckCircle2 className="w-3.5 h-3.5" />
          Production MVP Verified
        </span>
        <h2 className="mt-6 font-display font-black text-4xl md:text-5xl leading-[1.0] text-white">
          From web submission to{" "}
          <span className="text-green">CASE APPROVED</span>
        </h2>
        <p className="mt-6 text-white/60 text-base md:text-lg max-w-2xl leading-relaxed">
          Case <span className="font-mono text-white/80">MEDIFLOW-WEB-989E388C</span>{" "}
          moved from web submission to CASE APPROVED. BODY PAINS, PARACETAMOL,
          and Peaceway Pharmacy were preserved through the workflow.
        </p>
        <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {PROOF_ROWS.map((row) => (
            <div
              key={row.label}
              className="rounded-xl border border-white/10 bg-card px-4 py-3"
            >
              <div className="text-[11px] uppercase tracking-widest text-white/40">
                {row.label}
              </div>
              <div className="mt-1 text-sm text-white/85 break-words">
                {row.value}
              </div>
            </div>
          ))}
          <div className="rounded-xl border border-green/30 bg-green/10 px-4 py-3">
            <div className="text-[11px] uppercase tracking-widest text-green/80">
              Final result
            </div>
            <div className="mt-1 text-sm font-bold text-green">
              CASE APPROVED
            </div>
          </div>
        </div>
        <p className="mt-8 max-w-2xl border-l-2 border-green/50 pl-4 text-white/70 text-sm md:text-base">
          No AI approved this case. Final approval was made by the human
          reviewer.
        </p>
      </m.div>
    </section>
  );
}

const SAFETY_POINTS = [
  "AI does not make final approval decisions.",
  "The Approval Desk does not approve cases.",
  "A human reviewer must manually approve or reject.",
  "MediFlow is workflow support, not a replacement for licensed medical professionals.",
  "This is a hackathon MVP, not a full medical product.",
];

function SafetySection() {
  return (
    <section
      id="safety"
      className={`${MATTE} relative px-6 md:px-12 py-32 overflow-hidden`}
    >
      <NoiseOverlay />
      <m.div
        className="relative z-[2] max-w-5xl mx-auto"
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.7, ease: EASE }}
      >
        <span className="inline-flex items-center gap-2 rounded-full border border-teal/30 bg-teal/10 px-3 py-1 text-xs uppercase tracking-widest text-teal">
          <ShieldCheck className="w-3.5 h-3.5" />
          Human-in-the-loop safety
        </span>
        <h2 className="mt-6 font-display font-black text-4xl md:text-5xl leading-[1.0] text-white">
          The final decision is always human
        </h2>
        <ul className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-4">
          {SAFETY_POINTS.map((point) => (
            <li
              key={point}
              className="flex items-start gap-3 rounded-xl border border-white/10 bg-card px-4 py-4"
            >
              <ShieldCheck className="w-5 h-5 text-teal shrink-0 mt-0.5" />
              <span className="text-white/70 text-sm leading-relaxed">
                {point}
              </span>
            </li>
          ))}
        </ul>
      </m.div>
    </section>
  );
}

export function MedBandLanding() {
  return (
    <LazyMotion features={domAnimation}>
      <IntroSequence />
      <TopBar />
      <MobileFloatingCTA />
      <main>
        <HeroSection />
        <ProofSection />
        <ViewportSection>
          <Suspense fallback={<SectionFallback />}>
            <HowItWorks />
          </Suspense>
        </ViewportSection>
        <ViewportSection>
          <Suspense fallback={<SectionFallback />}>
            <SixSectors />
          </Suspense>
        </ViewportSection>
        <SafetySection />
        <ViewportSection>
          <Suspense fallback={<SectionFallback />}>
            <TrustedInstitutions />
          </Suspense>
        </ViewportSection>
        <ViewportSection>
          <Suspense fallback={<SectionFallback />}>
            <BandIntegration />
          </Suspense>
        </ViewportSection>
      </main>
      <ViewportSection minHeight="min-h-[40vh]">
        <Suspense fallback={<SectionFallback />}>
          <Footer />
        </Suspense>
      </ViewportSection>
    </LazyMotion>
  );
}
