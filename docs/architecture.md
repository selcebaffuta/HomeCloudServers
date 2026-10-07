# Architecture

## Stack

The public site uses Next.js 16.3.3 with the App Router, React 19, strict TypeScript and npm. CSS Modules provide component-level styles; `src/styles/tokens.css` provides the shared semantic design tokens. The Node.js test runner executes TypeScript through `tsx`. Tailwind and component frameworks are intentionally absent to keep the runtime and authoring model small.

Server Components are the default. A single small Client Component owns the mobile menu interaction so it can expose `aria-expanded`, close after navigation and handle Escape correctly. Motion remains CSS-only. This keeps the initial JavaScript budget close to the framework baseline.

## App Router structure

- `/` is the complete marketing landing page.
- `/apps` is a public explanation of the future local app ecosystem.
- `/compare` renders a desktop comparison table and a separate mobile-first comparison view.
- `/products/[slug]` statically generates Base, Plus and Pro from one template and one catalog.
- `/robots.txt`, `/sitemap.xml`, `/manifest.webmanifest` and the Open Graph image are generated through metadata routes.

Future commerce routes are reserved conceptually, not implemented: `/store`, `/configure/[product]`, `/cart`, `/checkout`, `/account` and `/orders/[id]`.

## Component architecture

`components/layout` owns site chrome. `components/marketing` composes the landing experience; its three visually complex, autonomous sections (`HomeHero`, `ProductFamilySection` and `IntegratedDisplayShowcase`) are extracted while simpler editorial sections stay together. `components/products` owns product-specific presentation, including the replaceable `ProductVisual` and the shared interface preview. `components/ui` contains the very small set of reusable primitives.

The abstract product mockup is semantic HTML/CSS and is labelled as conceptual. Its API accepts a product record, so approved AVIF/WebP assets can replace its internals without changing callers or content models.

## Data model

`src/data/products.ts` is the canonical catalog. Product copy, highlights, model-specific storytelling, capabilities, routes and comparison values reference the same records. The `Product` interface already reserves optional fields for price, currency, storage, RAM, accessories, availability, SKU, images and shipping class. Those values remain absent until authoritative commercial data exists.

`src/data/features.ts` contains comparison projections and shared marketing collections. No page owns a second copy of product facts.

## Branding

`src/config/brand.ts` owns the provisional product name, short name, descriptor, tagline, metadata defaults, optional support address, social placeholders and product-family names. The support address is exposed only when `NEXT_PUBLIC_SUPPORT_EMAIL` is configured, so the public UI never links to a placeholder mailbox. Templates interpolate brand configuration rather than repeating the brand string. A future rename should primarily touch this file, approved artwork and editorial copy that intentionally discusses the old name.

## SEO

The root layout sets a title template, description, Open Graph and Twitter defaults. Each public route adds canonical metadata via `createMetadata`. The canonical origin comes from `NEXT_PUBLIC_SITE_URL`, with a development fallback. Product and catalog pages expose conservative schema.org data without offers, ratings or invented availability.

## Deployment

The project builds as a standard Next.js Node server and can run anywhere supporting Node.js 20.9 or newer. No provider-specific deployment configuration is included. Production must set `NEXT_PUBLIC_SITE_URL` to the public HTTPS origin before build.

## Commerce boundary

This milestone has no cart, checkout, account, payment, order or fulfillment behavior. The public catalog is deliberately read-only. See `commerce-roadmap.md` for the future boundary between presentation, commerce services and device management.
