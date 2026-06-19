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
  roadmap?: boolean;
};

export const SECTORS: SectorItem[] = [
  {
    name: "Pharmacy",
    icon: Pill,
    image: ASSETS.sectorPharmacy,
    desc: "The live MVP. Structures the request, checks whether it can proceed safely, confirms stock, and routes to a human pharmacist for final approval.",
    env: "pharmacy",
    active: true,
  },
  {
    name: "Hospital Triage",
    icon: Heart,
    image: ASSETS.sectorTriage,
    desc: "Planned: classify severity, check bed availability, route to a doctor for the final call.",
    env: "hospital_triage",
    roadmap: true,
  },
  {
    name: "Lab/Diagnostics",
    icon: FlaskConical,
    image: ASSETS.sectorLab,
    desc: "Planned: validate referrals, check the test catalog, confirm lab slot availability.",
    env: "lab",
    roadmap: true,
  },
  {
    name: "Mental Health",
    icon: Brain,
    image: ASSETS.sectorMental,
    desc: "Planned: risk screening and matching to therapist availability, with human-led review.",
    env: "mental_health",
    roadmap: true,
  },
  {
    name: "HMO/Insurance",
    icon: Shield,
    image: ASSETS.sectorHmo,
    desc: "Planned: verify policy eligibility, check coverage limits, route to a claims officer.",
    env: "hmo_claims",
    roadmap: true,
  },
  {
    name: "Emergency",
    icon: Siren,
    image: ASSETS.sectorEmergency,
    desc: "Planned: classify severity and dispatch the nearest available unit, with human oversight.",
    env: "emergency",
    roadmap: true,
  },
];

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
    title: "Patient Submits a Request",
    body: "A patient fills in the web form for the Pharmacy workflow and describes their need. The case enters MediFlow instantly.",
  },
  {
    num: "02",
    icon: Zap,
    title: "Agents Coordinate the Case",
    body: "The Coordinator opens a Band room and routes the case: Intake structures it, Verification checks whether it can proceed safely, and Resource confirms availability.",
  },
  {
    num: "03",
    icon: Shield,
    title: "Band Coordinates Everything",
    body: "Agents communicate through Band rooms. Every handoff is timestamped and auditable, and every workflow stage is tracked in Postgres.",
  },
  {
    num: "04",
    icon: CheckCircle,
    title: "A Human Makes the Final Decision",
    body: "The Approval Desk prepares the case for review and a human reviewer responds APPROVE or REJECT in the Band room. No AI makes the final call.",
    iconColor: "text-green",
  },
];

export const AGENT_ROLES: { name: string; body: string }[] = [
  {
    name: "Web Agent",
    body: "Receives the patient request from the web form and starts the case.",
  },
  {
    name: "Coordinator",
    body: "Routes the case between agents and tracks every workflow stage.",
  },
  {
    name: "Intake",
    body: "Structures the request into clean, verifiable data.",
  },
  {
    name: "Verification",
    body: "Checks whether the request can proceed safely.",
  },
  {
    name: "Resource",
    body: "Checks availability at the selected institution.",
  },
  {
    name: "Approval Desk",
    body: "Prepares the case for human review. It does not approve or reject.",
  },
  {
    name: "Human Reviewer",
    body: "Approves or rejects the case manually. The final decision is always human.",
  },
];

export const TIMELINE_NODES = [
  "NEW_CASE_FROM_WEB",
  "CASE OPENED",
  "INTAKE COMPLETE",
  "VERIFY CASE",
  "VERIFICATION COMPLETE",
  "CHECK AVAILABILITY",
  "RESOURCE COMPLETE",
  "CASE READY FOR HUMAN REVIEW",
  "CASE APPROVED",
] as const;
