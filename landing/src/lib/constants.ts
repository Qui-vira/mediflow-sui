export const EASE = [0.22, 1, 0.36, 1] as const;
export const INTRO_DELAY = 2.9;
export const MATTE = "bg-[oklch(0.09_0.006_220)]";

export const ASSET_BASE = "/static/";

export const ASSETS = {
  logo: `${ASSET_BASE}logo.svg`,
  favicon: `${ASSET_BASE}favicon.svg`,
  noise: `${ASSET_BASE}noise.png`,
  sectorPharmacy: `${ASSET_BASE}sector-pharmacy.png`,
  sectorTriage: `${ASSET_BASE}sector-triage.png`,
  sectorLab: `${ASSET_BASE}sector-lab.png`,
  sectorMental: `${ASSET_BASE}sector-mental.png`,
  sectorHmo: `${ASSET_BASE}sector-hmo.png`,
  sectorEmergency: `${ASSET_BASE}sector-emergency.png`,
  bandRoom: `${ASSET_BASE}band-room-screenshot.png`,
  dashboard: `${ASSET_BASE}dashboard-screenshot.png`,
  form: `${ASSET_BASE}form-screenshot.png`,
} as const;

export const LINKS = {
  live: "https://web-production-6d13b.up.railway.app",
  github: "https://github.com/Qui-vira/Tbr-Medband",
} as const;
