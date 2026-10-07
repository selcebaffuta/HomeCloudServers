# HomeCloudServers

Production-oriented public website for the provisional **HomeCloud** brand. The current marketing milestone presents the Base, Plus and Pro product families, explains the product model and prepares a typed boundary for future commerce without implementing checkout, accounts, payments or device management.

## Stack

- Next.js 16 App Router
- React 19 with Server Components by default
- strict TypeScript
- CSS Modules and global semantic design tokens
- ESLint 9 with Next.js Core Web Vitals rules
- Node.js test runner with `tsx` for catalog and configuration tests
- npm with a versioned lockfile

The site uses no UI framework, remote font, animation library or client-side state package. A single small Client Component manages the accessible mobile menu; the rest of the site is server-rendered.

## Requirements

- Node.js 20.9 or newer
- npm 9 or newer

## Development

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.

## Quality checks

```bash
npm run lint
npm run typecheck
npm test
npm run build
npm run test:smoke
```

Run the production build locally with:

```bash
npm start
```

## Environment variables

| Variable | Required in production | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_SITE_URL` | Yes | Canonical HTTPS origin for metadata, sitemap, robots and structured data. Falls back to `http://localhost:3000` in development. |
| `NEXT_PUBLIC_SUPPORT_EMAIL` | No | Enables the public support email link only when a real monitored address is configured. |

## Routes

- `/` — complete landing page
- `/apps` — marketing/catalog introduction for the app ecosystem
- `/compare` — Base, Plus and Pro comparison
- `/products/base`
- `/products/plus`
- `/products/pro`

Metadata routes expose `/robots.txt`, `/sitemap.xml`, `/manifest.webmanifest` and a generated Open Graph image.

## Project structure

```text
src/
  app/          App Router pages and metadata routes
  components/   layout, marketing, product and UI components
  config/       provisional brand and canonical site configuration
  data/         typed product catalog and shared feature data
  lib/          metadata helpers
  styles/       global CSS and semantic design tokens
public/images/  reserved approved product and UI assets
docs/           architecture, design system and commerce roadmap
```

## Product and brand data

Change provisional brand-level values in `src/config/brand.ts`. The catalog in `src/data/products.ts` powers product pages, cards, URLs and comparison content. Commerce-shaped fields are optional and intentionally empty until authoritative pricing, SKUs and configurations exist.

## Project status

The deployable marketing foundation now includes the visual-polish milestone. Product visuals form a coherent conceptual hardware family and are ready to be replaced by approved AVIF/WebP renders without changing product data or page structure. Pricing, availability, final hardware specifications, purchasing, customer accounts and shipment workflows remain out of scope.

See:

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/design-system.md`](docs/design-system.md)
- [`docs/commerce-roadmap.md`](docs/commerce-roadmap.md)
