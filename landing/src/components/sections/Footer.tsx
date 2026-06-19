import { LogoMark } from "../LogoMark";
import { LINKS } from "@/lib/constants";
import { SECTORS } from "@/lib/sectors";

const TEAM = [
  {
    name: "Kehinde-David Damilare Samuel",
    handle: "Big Quiv",
    role: "Technical Lead, Product Architect, and Final Submission Owner",
  },
  {
    name: "Olumuyiwa",
    handle: "@Kedavi",
    role: "Quality Assurance and Live Demo Tester",
  },
  {
    name: "Ubochi Sandra",
    handle: "@Sanera",
    role: "Content, Documentation, and Submission Writer",
  },
  {
    name: "Dennis Paul",
    handle: "@Bigdennis",
    role: "Demo Video Producer",
  },
];

export default function Footer() {
  return (
    <footer className="relative border-t border-white/10 px-6 md:px-12 py-12">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <LogoMark style={{ fontSize: "1.25rem", lineHeight: 1.2 }} />
        <div className="flex gap-6">
          {[
            { label: "Live Demo", href: LINKS.live },
            { label: "GitHub", href: LINKS.github },
            { label: "Band", href: LINKS.band },
            { label: "Register Institution", href: LINKS.register },
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
          <p className="font-display font-bold mb-2">
            <LogoMark style={{ fontSize: "1rem", lineHeight: 1.2 }} />
          </p>
          <p className="text-white/40 text-sm leading-relaxed">
            A human-in-the-loop healthcare workflow MVP. AI coordinates; humans
            decide. Built for Band of Agents Hackathon 2026.
          </p>
        </div>
        <div>
          <p className="font-medium text-white text-sm mb-3">MVP Scope</p>
          <ul className="space-y-2">
            {SECTORS.map((s) => (
              <li key={s.env}>
                <span className="text-white/40 text-sm cursor-default">
                  {s.name}
                  {s.active ? (
                    <span className="text-green"> · Live</span>
                  ) : (
                    <span className="text-amber/80"> · Roadmap</span>
                  )}
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

      <div className="mt-8 pt-8 border-t border-white/10">
        <p className="font-medium text-white text-sm mb-4">Team</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {TEAM.map((member) => (
            <div
              key={member.name}
              className="rounded-xl border border-white/10 bg-card px-4 py-4"
            >
              <p className="font-display font-bold text-sm text-white leading-snug">
                {member.name}
              </p>
              <p className="text-teal text-xs mt-0.5">{member.handle}</p>
              <p className="text-white/45 text-xs mt-2 leading-relaxed">
                {member.role}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-8 pt-6 border-t border-white/10 flex items-center justify-between flex-wrap gap-4">
        <p className="text-white/30 text-xs">
          © 2026 MediFlow by The Billionaire Republic. All rights reserved.
        </p>
        <p className="text-white/30 text-xs">
          Band of Agents Hackathon 2026 · Track 3: Regulated Workflows
        </p>
      </div>
    </footer>
  );
}
