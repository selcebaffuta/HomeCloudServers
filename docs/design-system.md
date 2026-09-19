# Design system

## Direction

The visual system extends the existing device UI into a public, editorial hardware experience: calm canvas, clean white or charcoal surfaces, near-black type, restrained cool-blue accent and status colors used only for status. It avoids dashboard density, generic hosting imagery and decorative gradients.

## Typography

The stack is entirely local/system: `Inter` when already installed, then system UI fallbacks. No remote font request is required. Headlines use a compact, fluid scale with negative tracking; body copy remains at readable sizes and constrained line lengths. Labels and specifications use small uppercase eyebrow text only where hierarchy benefits.

## Color

Semantic tokens live in `src/styles/tokens.css`. Important tokens include canvas, surface, muted surface, ink, two text levels, separators, accent and controlled success/warning/danger colors. Dark mode follows `prefers-color-scheme` and uses explicit values rather than filter inversion. OLED presentation is always locally dark.

## Spacing and layout

The maximum editorial width is 88rem and core reading width is 74rem. Section spacing uses a fluid `clamp()` token. Layouts begin mobile-first in behavior, expand to asymmetric editorial grids on desktop, and retain intentional whitespace at ultrawide sizes.

## Radius and elevation

Small controls use 12px-equivalent radii. Content panels use 20px or a fluid large radius. Pill radii are reserved for CTAs and status. Shadows appear only on elevated hardware/interface mockups; normal section separation relies on spacing and fine rules.

## Components

- Header: sticky, compact, lightly blurred and keyboard accessible.
- Mobile navigation: focused client island with `aria-expanded`, Escape handling, close-on-navigation behavior and a 44px touch target.
- CTA: pill-shaped primary, outlined secondary and text variants.
- Product visual: shared abstract hardware mockup with Base, Plus and Pro variants.
- Comparison: semantic table on desktop and labelled definition-list panels on mobile.
- App category: simple category monogram without third-party marks.

## Motion

Normal transitions are 160–240ms using an ease-out curve. Product reveal affects opacity and transform only. Hover depth is subtle. `prefers-reduced-motion: reduce` disables transitions, animations and smooth scrolling globally.

## Responsive rules

Primary breakpoints occur around content needs, not device brands: 1060px for wide editorial/product grids, 900px for two-column feature layouts, 760px for navigation and reading layouts, and 520/430px for narrow controls. The comparison table is replaced—not merely squeezed—on small screens. Horizontal app rails use scroll snapping and the page itself never requires horizontal scrolling.

## Accessibility

The target is WCAG 2.2 AA where reasonably applicable. The system includes semantic landmarks, a skip link, visible focus, structured headings, labelled visuals, 44px minimum controls, non-color status labels and reduced-motion support. Copy avoids absolute security/privacy claims.
