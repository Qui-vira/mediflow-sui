# MedBand Landing Page

Premium marketing landing page for **MedBand** by The Billionaire Republic.

## Stack

- React 19 + Vite + TypeScript
- Tailwind CSS v4
- Framer Motion
- Lucide React
- TanStack Router

## Development

```bash
cd landing
npm install
npm run dev
```

Open http://localhost:5173

## Production build

```bash
npm run build
npm run preview
```

Output is in `dist/`. Deploy to any static host (Vercel, Netlify, Railway static, etc.).

## Assets

Images load from the live MedBand deployment:

`https://web-production-6d13b.up.railway.app/static/`

If an asset fails to load, the page falls back to placeholders or Lucide icons per the spec.

## Structure

| File | Purpose |
|------|---------|
| `src/components/MedBandLanding.tsx` | Main page (Hero, How It Works, Sectors, Band Integration, Footer) |
| `src/components/IntroSequence.tsx` | 3.6s opening animation |
| `src/components/StarField.tsx` | Canvas star field with optional ring |
| `src/components/LineField.tsx` | SVG constellation lines + markers |
| `src/routes/index.tsx` | Route definition + SEO metadata |
| `src/styles.css` | Theme tokens (teal/navy dark mode) |
