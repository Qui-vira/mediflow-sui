import { createRoute } from "@tanstack/react-router";
import { Route as rootRoute } from "./__root";
import { MedBandLanding } from "@/components/MedBandLanding";

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: MedBandLanding,
  head: () => ({
    meta: [
      { title: "MediFlow — Multi-Agent Healthcare Workflow" },
      {
        name: "description",
        content:
          "MediFlow by The Billionaire Republic. Four AI agents coordinate through Band rooms to process healthcare requests across six sectors. Human-in-the-loop approval. Band of Agents Hackathon 2026.",
      },
      { property: "og:title", content: "MediFlow — Healthcare, Intelligently Routed" },
      {
        property: "og:description",
        content:
          "Multi-agent healthcare workflow engine. 6 sectors. 4 agents. Human approval. Powered by Band.",
      },
    ],
  }),
});
