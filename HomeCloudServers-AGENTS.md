# HomeCloudServers — Codex project instructions

## Repository identity

This repository is **HomeCloudServers**, the public, production-oriented
HomeCloud marketing website.

It presents the Base, Plus, and Pro product families and maintains a typed
boundary for possible future commerce. It does not own the appliance runtime,
factory provisioning, mobile application, customer accounts, checkout,
payments, device management, or fleet infrastructure unless those capabilities
are explicitly added and approved.

Related repositories:

- **HomeCloud**: appliance runtime, backend, frontend, and buyer onboarding;
- **HomeCloudSetup**: factory preparation, installation, and updates;
- **HomeCloudAndroid**: native Android client;
- **HomeCloudDev**: development support only as documented by that repository.

---

## Persistent project memory

Use the Obsidian MCP server as persistent project memory. The current chat is
not the complete or authoritative project history.

At the beginning of substantial work:

1. confirm that the current repository is HomeCloudServers;
2. inspect the current working tree, product data, brand configuration, routes,
   tests, and documentation;
3. search Obsidian for relevant product, frontend, documentation, and active
   work notes;
4. check `In corso` for unfinished work and blockers;
5. identify claims or contracts that depend on another HomeCloud repository;
6. identify accessibility, SEO, privacy, security, and deployment effects.

Read only the relevant vault context. Search before creating notes and do not
create new top-level vault folders unless explicitly requested.

Use Obsidian MCP tools instead of shell access to the vault when an appropriate
operation exists. If MCP is unavailable, report it and include pending memory
updates in the final handoff.

---

## Vault placement

Use the existing vault structure:

- `HomeCloud frontend`: shared product presentation and public experience;
- `HomeCloud frontend/Base`, `Plus`, and `Pro`: edition-specific claims,
  presentation, features, and approved visual direction;
- `Readme e manuali`: site architecture, content guidelines, publishing,
  accessibility, SEO, and maintenance documentation;
- `Aggiornamenti`: release, deployment, canonical URL, and versioned public
  rollout information when it has lasting project value;
- `App mobile/Android` or `App mobile/iOS`: public-site claims about mobile
  clients that require verification with those projects;
- `Sicurezza`: privacy, public attack surface, headers, dependencies, forms,
  data collection, cookies, or future commerce security;
- `In corso`: current site work, content gaps, blockers, and next actions.

Do not create generic top-level `Decisions` or `Discoveries` folders. Place
durable knowledge with the affected domain.

---

## Brand and product truth

HomeCloud branding and product facts may still be provisional. Keep replaceable
brand-level copy centralized in `src/config/brand.ts`. Keep Base, Plus, and Pro
catalog data centralized in `src/data/products.ts` unless the current codebase
establishes a newer authoritative source.

Do not scatter product names, descriptors, hostnames, support details, or
product facts across templates when they belong in shared configuration.

Do not invent or imply unverified:

- prices or discounts;
- launch or shipping dates;
- CPU, RAM, storage, capacity, or performance specifications;
- availability or inventory;
- certifications;
- partnerships or integrations;
- warranties or support promises;
- privacy or security guarantees;
- checkout, payment, account, fulfillment, or tracking capabilities.

When facts are not authoritative, omit them or use restrained language such as
"Configuration dependent" where appropriate. Treat repository code and
documentation from other HomeCloud projects as evidence to verify, not as
automatic permission to turn implementation details into marketing claims.

The Pro physical/contextual surface is called **Control Bar**, never "Touch
Bar". Present Base, Plus, and Pro as hardware families, not as SaaS pricing
tiers.

---

## Design direction

Preserve a premium consumer-hardware presentation:

- generous whitespace;
- editorial typography;
- restrained blue accents;
- large product showcase sections;
- clear hierarchy and calm motion;
- approved or clearly labelled conceptual hardware imagery;
- responsive layouts with accessible interaction.

Avoid drifting into generic SaaS dashboards, hosting-company visuals, Shopify
storefront patterns, or interchangeable pricing cards.

Do not claim visual QA from code inspection, screenshots from an unrelated
build, or a successful production build. When browser or visual inspection is
not available, report that limitation explicitly.

---

## Technical boundaries

Preserve the established Next.js App Router architecture, strict TypeScript,
server-rendered defaults, semantic design tokens, accessible navigation, and
versioned npm lockfile unless a change has a clear need and is reviewed.

Prefer Server Components. Add Client Components only where browser interaction
requires them. Avoid adding frameworks, state libraries, animation packages,
remote fonts, or analytics merely for convenience.

Environment-specific public values such as the canonical site origin belong in
documented environment configuration. Never embed production credentials or
private service keys in client bundles or `NEXT_PUBLIC_*` variables.

Future commerce must remain behind an explicit architecture decision. Do not
silently implement cart, checkout, payments, customer accounts, orders,
fulfillment, shipment tracking, or device management because data structures
contain optional commerce-shaped fields.

---

## Accessibility, SEO, and public safety

For user-facing changes, check:

- semantic HTML and heading order;
- keyboard navigation and visible focus;
- accessible names, labels, and error messages;
- colour contrast and reduced-motion behaviour;
- responsive layout and content reflow;
- metadata, canonical URLs, robots, sitemap, manifest, and structured data;
- meaningful alt text and honest labelling of conceptual visuals;
- absence of secrets, internal URLs, private repository details, or unpublished
  operational information.

Do not collect personal data, add tracking, submit forms, or call a production
backend without an explicit request and a documented privacy/security design.

---

## Cross-repository knowledge

Verify claims against the repository that owns the behaviour:

- HomeCloud for runtime features, UI, APIs, supported editions, and onboarding;
- HomeCloudSetup for installation, device profiles, updates, and factory flows;
- HomeCloudAndroid for Android availability and mobile features;
- the relevant future iOS repository for iOS claims.

When a public claim establishes a product contract, document it in Obsidian and
record missing implementation or content follow-up under `In corso`. Never
assume another repository has already adopted the same wording or behaviour.

---

## Source of truth

When information conflicts, use:

1. current source, tests, and generated output for implemented site behaviour;
2. explicit current user instructions for intended scope;
3. authoritative product data and approved brand material;
4. current Obsidian documentation;
5. older notes and historical copy.

Code is not proof that a product claim is approved. Resolve conflicts between
implementation, catalog data, public copy, and other repositories before
publishing the claim.

---

## Decisions, discoveries, and secrets

Persist decisions about brand architecture, product taxonomy, routes, content
models, accessibility, SEO, deployment, or future-commerce boundaries with the
affected vault area.

Persist discoveries that are not obvious from the source, including browser
behaviour, rendering constraints, metadata issues, build limitations, and
cross-repository claim mismatches. Record observation, cause, consequence,
evidence, and fix or workaround.

Do not persist temporary build output, conversational transcripts, trivial
formatting changes, or internal reasoning.

Never store passwords, tokens, private keys, session cookies, customer data,
private repository content, unreleased credentials, or production secrets in
Git, Obsidian, logs, screenshots, or handoff notes. Use `[REDACTED_SECRET]` or an
environment-variable name in examples.

---

## Validation

After substantial changes:

1. run linting, type checking, tests, and the production build;
2. run the production route smoke test when available;
3. inspect the diff for duplicated brand or catalog data and unrelated changes;
4. verify metadata and generated public routes when affected;
5. perform browser, responsive, keyboard, and visual checks when the tooling is
   available;
6. state clearly which checks ran, their results, and what remained unverified;
7. update permanent notes and `In corso`.

A successful build does not prove visual quality, factual accuracy,
accessibility, or production deployment.

---

## End-of-session handoff

Before ending substantial work, update the vault with:

- objective and completed work;
- important files and routes changed;
- product claims added, removed, or still awaiting confirmation;
- tests and visual/accessibility checks performed;
- checks that were not possible;
- cross-repository impact;
- blockers and next action.

Tell the user which Obsidian notes were created or updated and why. If MCP was
unavailable, list pending updates without pretending they were saved.

Keep the handoff concise, factual, searchable, and free of secrets.
