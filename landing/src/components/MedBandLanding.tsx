import { useEffect, useRef, useState, type CSSProperties } from "react";
import {
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
} from "framer-motion";
import {
  Activity,
  ArrowUpRight,
  Brain,
  CheckCircle,
  ChevronRight,
  FlaskConical,
  Github,
  Heart,
  Menu,
  MoveRight,
  Pill,
  Shield,
  Siren,
  Users,
  X,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { IntroSequence } from "./IntroSequence";
import { LineField } from "./LineField";
import { StarField } from "./StarField";
import { ASSETS, EASE, INTRO_DELAY, LINKS, MATTE } from "@/lib/constants";
import { blurIn, photoIn, viewBlurIn, viewFadeUp } from "@/lib/motion";

function SafeImage({
  src,
  alt,
  className,
  style,
  decorative = false,
  fallbackIcon: FallbackIcon,
}: {
  src: string;
  alt: string;
  className?: string;
  style?: CSSProperties;
  decorative?: boolean;
  fallbackIcon?: LucideIcon;
}) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    if (FallbackIcon) {
      return (
        <div
          className={`flex items-center justify-center bg-[oklch(0.18_0_0)] ${className ?? ""}`}
          style={style}
          aria-hidden={decorative}
        >
          <FallbackIcon className="w-8 h-8 text-teal opacity-60" />
        </div>
      );
    }
    return (
      <div
        className={`bg-[oklch(0.18_0_0)] ${className ?? ""}`}
        style={style}
        aria-hidden={decorative}
      />
    );
  }

  return (
    <img
      src={src}
      alt={decorative ? "" : alt}
      aria-hidden={decorative || undefined}
      className={className}
      style={style}
      onError={() => setFailed(true)}
    />
  );
}

function Logo({ className = "h-6 w-auto" }: { className?: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <span className={`font-display font-black ${className}`}>
        <span className="text-teal">Med</span>
        <span className="text-[oklch(0.13_0.03_240)]">Band</span>
      </span>
    );
  }
  return (
    <img
      src={ASSETS.logo}
      alt="MedBand"
      className={className}
      onError={() => setFailed(true)}
    />
  );
}

function NoiseOverlay() {
  const [failed, setFailed] = useState(false);
  if (failed) return null;
  return (
    <img
      src={ASSETS.noise}
      alt=""
      aria-hidden
      className="absolute inset-0 w-full h-full object-cover opacity-[0.12] mix-blend-overlay pointer-events-none"
      style={{ zIndex: 1 }}
      onError={() => setFailed(true)}
    />
  );
}

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
    { label: "Sectors", action: () => scrollTo("sectors") },
    { label: "Band Integration", action: () => scrollTo("band-integration") },
    { label: "GitHub", href: LINKS.github },
  ];

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 pt-6 px-6 md:px-10 transition-all duration-300 ${
        scrolled ? "backdrop-blur-md bg-black/40 border-b border-white/10" : ""
      }`}
    >
      <div className="flex items-center justify-between gap-4">
        <motion.a
          href="#"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: INTRO_DELAY - 0.2, ease: EASE }}
        >
          <Logo />
        </motion.a>

        <motion.nav
          className="hidden md:flex items-center gap-1"
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
                className="text-sm text-white/60 hover:text-white transition px-4 py-2"
              >
                {link.label}
              </a>
            ) : (
              <button
                key={link.label}
                type="button"
                onClick={link.action}
                className="text-sm text-white/60 hover:text-white transition px-4 py-2"
              >
                {link.label}
              </button>
            ),
          )}
        </motion.nav>

        <motion.div
          className="flex items-center gap-3"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: INTRO_DELAY, ease: EASE }}
        >
          <a
            href={LINKS.live}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:inline-flex rounded-full bg-teal text-white px-4 py-2 text-sm hover:bg-teal/80 transition"
          >
            Submit a Case
          </a>
          <button
            type="button"
            className="md:hidden text-white/80 hover:text-white p-2"
            onClick={() => setOpen(!open)}
            aria-label={open ? "Close menu" : "Open menu"}
          >
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </motion.div>
      </div>

      {open && (
        <div className="md:hidden mt-4 rounded-xl border border-white/10 bg-black/80 backdrop-blur-md overflow-hidden">
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
          <div className="mt-2 px-4 py-3 border-t border-white/10 flex items-center justify-between text-xs text-white/50">
            <span>Band of Agents Hackathon 2026</span>
          </div>
          <div className="px-4 py-3 border-t border-white/10 flex items-center justify-between text-xs text-white/50">
            <span>Built by</span>
            <span className="text-white/70">The Billionaire Republic</span>
          </div>
        </div>
      )}
    </header>
  );
}

const HERO_CARDS = [
  {
    src: ASSETS.bandRoom,
    alt: "Band room agents",
    position: "top-[5%] right-[2%]",
    size: "w-[280px] aspect-[16/10]",
    depth: 22,
    badge: "band" as const,
  },
  {
    src: ASSETS.form,
    alt: "Patient form",
    position: "top-[8%] left-[2%]",
    size: "w-[200px] aspect-[4/3]",
    depth: 18,
  },
  {
    src: ASSETS.dashboard,
    alt: "Pharmacist dashboard",
    position: "bottom-[8%] right-[4%]",
    size: "w-[260px] aspect-[16/10]",
    depth: 26,
    badge: "live" as const,
  },
  {
    src: ASSETS.sectorPharmacy,
    alt: "Pharmacy sector",
    position: "top-[15%] left-[5%]",
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
    const onMove = (e: MouseEvent) => {
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
      className={`${MATTE} relative min-h-[110vh] pt-32 pb-24 overflow-hidden`}
      style={style}
    >
      <StarField count={700} />
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
        <motion.div
          key={card.alt}
          className={`absolute z-20 ${card.position} ${card.size} group`}
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
        </motion.div>
      ))}

      <div className="relative z-10 grid place-items-center min-h-[60vh] px-6 text-center max-w-3xl mx-auto">
        <motion.div
          className="inline-flex items-center gap-2 rounded-full border border-teal/30 bg-teal/10 px-3 py-1 text-xs text-teal uppercase tracking-widest mb-8"
          initial={{ opacity: 0, y: 20, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.8, delay: INTRO_DELAY, ease: EASE }}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-teal" />
          Band of Agents Hackathon 2026 · Track 3
        </motion.div>

        <motion.h1
          className="font-display font-black text-6xl md:text-[90px] leading-[0.95] tracking-tight"
          variants={blurIn}
          initial="hidden"
          animate="show"
          custom={1}
        >
          Healthcare Requests,
          <br />
          <span className="text-teal">Intelligently</span> Routed
        </motion.h1>

        <motion.p
          className="mt-8 text-white/55 text-base md:text-lg leading-relaxed max-w-xl mx-auto"
          variants={blurIn}
          initial="hidden"
          animate="show"
          custom={3}
        >
          Four AI agents verify, check, and prepare every healthcare case before
          a human professional makes the final decision. Six sectors. One engine.
        </motion.p>

        <motion.div
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
            Submit a Case
            <ArrowUpRight className="w-4 h-4" />
          </a>
          <a
            href={LINKS.github}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-full border border-white/20 text-white/70 px-8 py-3 hover:bg-white/5 transition"
          >
            View on GitHub
            <Github className="w-4 h-4" />
          </a>
        </motion.div>
      </div>

      <div className="relative z-10 mt-20 flex gap-12 justify-center flex-wrap px-6">
        {[
          { num: "4", label: "Multi-Agent", sub: "agents" },
          { num: "6", label: "Healthcare Sectors", sub: "sectors" },
          { num: "100%", label: "Human Approval", sub: "human-in-loop" },
        ].map((stat, i) => (
          <motion.div
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
          </motion.div>
        ))}
      </div>
    </section>
  );
}

const STEPS = [
  {
    num: "01",
    icon: Activity,
    title: "Patient Submits Request",
    body: "Patient fills in a web form selecting their healthcare sector and describing their need. The request enters MedBand instantly.",
  },
  {
    num: "02",
    icon: Zap,
    title: "Four Agents Activate",
    body: "Coordinator creates a Band room. Intake structures the request. Verification checks registries and eligibility. Resource confirms availability.",
  },
  {
    num: "03",
    icon: Shield,
    title: "Band Coordinates Everything",
    body: "Every agent communicates exclusively through Band rooms. Every message is timestamped and auditable. Band is not a wrapper — it is the collaboration layer.",
  },
  {
    num: "04",
    icon: CheckCircle,
    title: "Human Makes Final Decision",
    body: "The human professional sees a structured case summary on the dashboard and clicks Approve or Reject. No AI makes the final call.",
    iconColor: "text-green",
  },
];

const TIMELINE_NODES = [
  "CASE_OPENED",
  "INTAKE_COMPLETE",
  "CASE_CLEAR",
  "RESOURCE_COMPLETE",
  "CASE_READY",
];

function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className={`${MATTE} relative px-6 md:px-12 py-32 overflow-hidden`}
    >
      <StarField count={500} />
      <LineField variant="photographer" />
      <NoiseOverlay />
      <div
        className="absolute -left-20 top-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full bg-teal/[0.03] blur-3xl pointer-events-none"
        style={{ zIndex: 1 }}
      />

      <div className="relative z-[2] max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-12 mb-20">
        <motion.h2
          className="font-display font-medium text-5xl md:text-6xl uppercase leading-[0.95] text-white"
          variants={viewBlurIn}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-100px" }}
        >
          How MedBand
          <br />
          Works
        </motion.h2>
        <motion.p
          className="text-white/55 text-[15px] max-w-md leading-relaxed self-end"
          variants={viewBlurIn}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-100px" }}
        >
          MedBand uses four specialized AI agents coordinating through Band
          rooms to process any healthcare request. Every handoff is visible,
          traceable, and auditable.
        </motion.p>
      </div>

      <div className="relative z-[2] max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
        {STEPS.map((step) => (
          <motion.div
            key={step.num}
            className="relative bg-card rounded-2xl p-8 border border-white/10 hover:border-teal/30 transition shadow-[0_40px_100px_-30px_rgba(0,0,0,0.8)]"
            initial={{ opacity: 0, y: 60, filter: "blur(16px)" }}
            whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 1.2, ease: EASE }}
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
          </motion.div>
        ))}
      </div>

      <div className="relative z-[2] max-w-5xl mx-auto mt-16 flex items-start justify-between gap-0 px-4">
        {TIMELINE_NODES.map((node, i) => (
          <div key={node} className="flex items-center flex-1 last:flex-none">
            <motion.div
              className="flex flex-col items-center"
              initial={{ opacity: 0, scale: 0 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: i * 0.15, ease: EASE }}
            >
              <div className="w-3 h-3 bg-teal rounded-full" />
              <span className="text-xs text-white/50 text-center mt-2 w-24 leading-tight">
                {node}
              </span>
            </motion.div>
            {i < TIMELINE_NODES.length - 1 && (
              <div className="flex-1 h-px bg-white/20 mt-1.5 mx-1" />
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

const SECTOR_NAMES = [
  "Pharmacy",
  "Hospital Triage",
  "Lab/Diagnostics",
  "Mental Health",
  "HMO/Insurance",
  "Emergency",
];

const SECTORS = [
  {
    name: "Pharmacy",
    icon: Pill,
    image: ASSETS.sectorPharmacy,
    desc: "Verifies drugs against national registry, checks prescription codes, confirms stock.",
    env: "pharmacy",
    active: true,
  },
  {
    name: "Hospital Triage",
    icon: Heart,
    image: ASSETS.sectorTriage,
    desc: "Classifies severity (red/yellow/green), checks bed availability, routes to doctor.",
    env: "hospital_triage",
  },
  {
    name: "Lab/Diagnostics",
    icon: FlaskConical,
    image: ASSETS.sectorLab,
    desc: "Validates referrals, checks test catalog, confirms lab slot availability.",
    env: "lab",
  },
  {
    name: "Mental Health",
    icon: Brain,
    image: ASSETS.sectorMental,
    desc: "Risk screening, self-harm detection, matches therapist availability and specialty.",
    env: "mental_health",
  },
  {
    name: "HMO/Insurance",
    icon: Shield,
    image: ASSETS.sectorHmo,
    desc: "Verifies policy eligibility, checks coverage limits, routes to claims officer.",
    env: "hmo_claims",
  },
  {
    name: "Emergency",
    icon: Siren,
    image: ASSETS.sectorEmergency,
    desc: "Classifies P1/P2/P3 severity, dispatches nearest available unit with ETA.",
    env: "emergency",
  },
];

function SixSectors() {
  const [cycleIndex, setCycleIndex] = useState(0);

  useEffect(() => {
    const t = setInterval(
      () => setCycleIndex((i) => (i + 1) % SECTOR_NAMES.length),
      2000,
    );
    return () => clearInterval(t);
  }, []);

  return (
    <section
      id="sectors"
      className={`${MATTE} relative px-6 md:px-12 py-32 overflow-hidden`}
    >
      <StarField
        count={550}
        ring
        ringCount={260}
        ringRadiusFactor={0.37}
        ringBandWidth={50}
      />
      <LineField variant="projects" />
      <NoiseOverlay />

      <div className="relative z-[2] max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-12 mb-20">
        <motion.h2
          className="font-display font-black text-5xl md:text-6xl uppercase leading-[0.95]"
          variants={viewBlurIn}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, margin: "-100px" }}
        >
          Six Healthcare
          <br />
          Sectors
        </motion.h2>
        <div>
          <motion.p
            className="text-white/55 text-[15px] max-w-md leading-relaxed"
            variants={viewBlurIn}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-100px" }}
          >
            One workflow engine. Switch one environment variable and MedBand runs
            for a completely different healthcare sector. No code changes.
          </motion.p>
          <motion.div
            className="mt-6 flex items-center gap-3 text-sm text-white/50"
            variants={viewBlurIn}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-100px" }}
          >
            <span>Switch sector:</span>
            <span className="inline-flex items-center rounded-full border border-teal/30 bg-teal/10 px-3 py-1 text-teal font-medium min-w-[140px] justify-center">
              {SECTOR_NAMES[cycleIndex]}
            </span>
          </motion.div>
        </div>
      </div>

      <div className="relative z-[2] max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-3 gap-6 md:gap-8">
        {SECTORS.map((sector, i) => (
          <motion.div
            key={sector.env}
            className="rounded-2xl p-6 border border-white/10 bg-[oklch(0.11_0.006_220)] hover:border-teal/40 hover:bg-[oklch(0.13_0.008_220)] transition-all duration-300 cursor-pointer group"
            initial={{ opacity: 0, y: 40, filter: "blur(12px)" }}
            whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 1.1, delay: i * 0.1, ease: EASE }}
          >
            <div className="w-12 h-12 rounded-xl bg-teal/10 flex items-center justify-center group-hover:bg-teal/20 transition">
              <sector.icon className="w-6 h-6 text-teal" />
            </div>
            <h3 className="font-display font-bold text-lg mt-4 text-white">
              {sector.name}
            </h3>
            <p className="text-white/55 text-sm mt-2 leading-relaxed">
              {sector.desc}
            </p>
            {sector.active && (
              <span className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-green/20 border border-green/30 px-2 py-0.5 text-xs text-green">
                <span className="w-1.5 h-1.5 rounded-full bg-green" />
                Demo Sector
              </span>
            )}
            <div className="mt-4 flex items-center justify-between text-xs text-white/30">
              <span>
                ACTIVE_SECTOR=
                <span className="text-teal font-mono">{sector.env}</span>
              </span>
              <ArrowUpRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition" />
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function BandIntegration() {
  const bottomRef = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({
    target: bottomRef,
    offset: ["start end", "end start"],
  });

  const parallaxY = useTransform(scrollYProgress, [0, 1], ["0%", "-15%"]);

  return (
    <section id="band-integration">
      <div className="relative px-6 md:px-12 pt-28 pb-12 overflow-hidden">
        <StarField count={450} />
        <LineField variant="marvels" />
        <NoiseOverlay />

        <motion.h2
          className="relative z-10 font-display font-medium uppercase text-5xl md:text-[80px] leading-[0.95] max-w-[1100px]"
          initial={{ opacity: 0, y: 40, filter: "blur(16px)" }}
          whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 1.2, ease: EASE }}
        >
          Powered by{" "}
          <SafeImage
            src={ASSETS.bandRoom}
            alt=""
            decorative
            className="inline-block h-10 md:h-16 w-auto rounded-md align-middle mx-1"
          />{" "}
          Band: Every agent. Every message. Every decision.
        </motion.h2>

        <div className="relative z-10 flex gap-4 flex-wrap mt-8">
          {[
            { icon: Zap, label: "Real-time WebSocket" },
            { icon: Shield, label: "Full Audit Trail" },
            { icon: Users, label: "4 Active Agents" },
          ].map(({ icon: Icon, label }) => (
            <span
              key={label}
              className="rounded-full border border-white/20 px-4 py-2 text-sm text-white/70 flex items-center gap-2"
            >
              <Icon className="w-3.5 h-3.5 text-teal" />
              {label}
            </span>
          ))}
        </div>

        <div className="relative z-10 flex justify-between items-center mt-16 text-xs uppercase tracking-widest text-white/50">
          <a
            href={LINKS.github}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center gap-2 hover:text-white transition"
          >
            View on GitHub
            <MoveRight className="w-3.5 h-3.5 -rotate-45 group-hover:translate-x-1 transition" />
          </a>
          <a
            href={LINKS.live}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center gap-2 hover:text-white transition"
          >
            Submit a Case
            <MoveRight className="w-3.5 h-3.5 -rotate-45 group-hover:translate-x-1 transition" />
          </a>
        </div>
      </div>

      <div ref={bottomRef} className="relative h-[80vh] overflow-hidden">
        <motion.div
          className="absolute -top-[10%] -bottom-[10%] inset-x-0"
          style={{
            y: parallaxY,
            background:
              "linear-gradient(135deg, oklch(0.08 0.04 220) 0%, oklch(0.04 0.02 240) 50%, oklch(0.06 0.06 180) 100%)",
          }}
        />
        {[
          { top: "20%", left: "15%", size: 300 },
          { top: "60%", left: "70%", size: 400 },
          { bottom: "10%", left: "40%", size: 250 },
        ].map((orb, i) => (
          <div
            key={i}
            className="absolute rounded-full bg-teal opacity-15 blur-3xl pointer-events-none"
            style={{
              width: orb.size,
              height: orb.size,
              top: orb.top,
              left: orb.left,
              bottom: orb.bottom,
            }}
            aria-hidden
          />
        ))}
        <div className="absolute inset-0 bg-gradient-to-t from-black/30 via-transparent to-black/20 pointer-events-none" />
        <LineField variant="marvelsBottom" />

        <div className="relative z-10 h-full grid place-items-center px-6 text-center">
          <div>
            <motion.h3
              className="font-display font-black uppercase text-4xl md:text-6xl leading-none tracking-tight"
              initial={{ opacity: 0, y: 40, filter: "blur(16px)" }}
              whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 1.2, ease: EASE }}
            >
              Build a band,
              <br />
              <span className="text-teal">not a soloist.</span>
            </motion.h3>
            <motion.p
              className="mt-6 text-white/55 text-lg max-w-lg mx-auto"
              variants={viewFadeUp}
              initial="hidden"
              whileInView="show"
              custom={0.2}
              viewport={{ once: true, margin: "-100px" }}
            >
              3+ agents collaborating through Band — planning, execution,
              review, decisions, handoffs.
            </motion.p>
            <motion.div
              className="mt-10 flex items-center justify-center gap-4 flex-wrap"
              variants={viewFadeUp}
              initial="hidden"
              whileInView="show"
              custom={0.3}
              viewport={{ once: true, margin: "-100px" }}
            >
              <a
                href={LINKS.live}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-full bg-teal text-white px-8 py-3 font-medium hover:bg-teal/80 transition"
              >
                Submit a Case
              </a>
              <a
                href={LINKS.github}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-full border border-white/20 text-white/70 px-8 py-3 hover:bg-white/5 transition"
              >
                View GitHub
              </a>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="relative border-t border-white/10 px-6 md:px-12 py-12">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <Logo />
        <div className="flex gap-6">
          {[
            { label: "GitHub", href: LINKS.github },
            { label: "Live Demo", href: LINKS.live },
            { label: "Hackathon", href: LINKS.github },
          ].map((link) => (
            <a
              key={link.label}
              href={link.href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-white/40 hover:text-white text-sm transition"
            >
              {link.label}
            </a>
          ))}
        </div>
      </div>

      <div className="mt-8 pt-8 border-t border-white/10 grid grid-cols-1 md:grid-cols-3 gap-8">
        <div>
          <p className="font-display font-bold text-white mb-2">MedBand</p>
          <p className="text-white/40 text-sm leading-relaxed">
            A sector-configurable multi-agent healthcare workflow engine. Built
            for Band of Agents Hackathon 2026.
          </p>
        </div>
        <div>
          <p className="font-medium text-white text-sm mb-3">Sectors</p>
          <ul className="space-y-2">
            {SECTORS.map((s) => (
              <li key={s.env}>
                <span className="text-white/40 text-sm hover:text-white transition cursor-default">
                  {s.name}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="font-medium text-white text-sm mb-3">Built by</p>
          <p className="text-white/60 text-sm">
            The Billionaire Republic (TBR)
          </p>
          <p className="text-white/40 text-sm mt-2 leading-relaxed">
            Turning ideas into real products, businesses, and income-generating
            opportunities.
          </p>
        </div>
      </div>

      <div className="mt-8 pt-6 border-t border-white/10 flex items-center justify-between flex-wrap gap-4">
        <p className="text-white/30 text-xs">
          © 2026 MedBand by The Billionaire Republic. All rights reserved.
        </p>
        <p className="text-white/30 text-xs">
          Band of Agents Hackathon 2026 · Track 3: Regulated Workflows
        </p>
      </div>
    </footer>
  );
}

export function MedBandLanding() {
  return (
    <>
      <IntroSequence />
      <TopBar />
      <main>
        <HeroSection />
        <HowItWorks />
        <SixSectors />
        <BandIntegration />
      </main>
      <Footer />
    </>
  );
}
