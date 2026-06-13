import {
  Activity,
  Brain,
  CheckCircle,
  FlaskConical,
  Heart,
  Pill,
  Shield,
  Siren,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { ASSETS } from "./constants";

export const SECTOR_NAMES = [
  "Pharmacy",
  "Hospital Triage",
  "Lab/Diagnostics",
  "Mental Health",
  "HMO/Insurance",
  "Emergency",
] as const;

export type SectorItem = {
  name: string;
  icon: LucideIcon;
  image: string;
  desc: string;
  env: string;
  active?: boolean;
};

export const SECTORS: SectorItem[] = [
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

export const FEATURED_INSTITUTIONS = [
  {
    id: "PHM001",
    name: "Peaceway Pharmacy",
    location: "Ikeja, Lagos",
    sector: "Pharmacy",
    logo_initial: "P",
    logo_color: "#276749",
    rating: 4.6,
    cases_processed: 890,
    plan: "professional",
    turnaround: "10-15 mins",
  },
  {
    id: "HSP001",
    name: "Reddington Hospital",
    location: "Victoria Island, Lagos",
    sector: "Hospital Triage",
    logo_initial: "R",
    logo_color: "#E53E3E",
    rating: 4.9,
    cases_processed: 3400,
    plan: "enterprise",
    turnaround: "2-5 mins",
  },
  {
    id: "LAB001",
    name: "Synlab Nigeria",
    location: "Victoria Island, Lagos",
    sector: "Lab/Diagnostics",
    logo_initial: "S",
    logo_color: "#0E7C7B",
    rating: 4.8,
    cases_processed: 1890,
    plan: "enterprise",
    turnaround: "2-24 hrs",
  },
  {
    id: "MH001",
    name: "Emeka Eze Wellness Centre",
    location: "Ikoyi, Lagos",
    sector: "Mental Health",
    logo_initial: "E",
    logo_color: "#553C9A",
    rating: 4.9,
    cases_processed: 340,
    plan: "enterprise",
    turnaround: "Same day",
  },
  {
    id: "HMO001",
    name: "Hygeia HMO",
    location: "Victoria Island, Lagos",
    sector: "HMO/Insurance",
    logo_initial: "H",
    logo_color: "#0E7C7B",
    rating: 4.6,
    cases_processed: 4500,
    plan: "enterprise",
    turnaround: "1-3 days",
  },
  {
    id: "EMG001",
    name: "LASAMBUS",
    location: "Lagos State",
    sector: "Emergency",
    logo_initial: "L",
    logo_color: "#E53E3E",
    rating: 4.5,
    cases_processed: 8900,
    plan: "enterprise",
    turnaround: "8-15 mins",
  },
] as const;

export const STEPS: {
  num: string;
  icon: typeof Activity;
  title: string;
  body: string;
  iconColor?: string;
}[] = [
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
    body: "The human professional sees a structured case summary in the Band room and responds APPROVE or REJECT. No AI makes the final call.",
    iconColor: "text-green",
  },
];

export const TIMELINE_NODES = [
  "CASE_OPENED",
  "INTAKE_COMPLETE",
  "CASE_CLEAR",
  "RESOURCE_COMPLETE",
  "CASE_READY",
] as const;
