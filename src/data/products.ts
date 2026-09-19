import { brand, type ProductFamilyKey } from "@/config/brand";

export type Availability = "announced" | "coming-soon" | "available" | "unavailable";

export interface CommerceFields {
  readonly basePrice?: number;
  readonly currency?: string;
  readonly storageOptions?: readonly string[];
  readonly ramOptions?: readonly string[];
  readonly accessories?: readonly string[];
  readonly availability?: Availability;
  readonly sku?: string;
  readonly images?: readonly string[];
  readonly shippingClass?: string;
}

export interface Product extends CommerceFields {
  readonly id: string;
  readonly slug: ProductFamilyKey;
  readonly family: ProductFamilyKey;
  readonly displayName: string;
  readonly shortName: string;
  readonly eyebrow: string;
  readonly description: string;
  readonly longDescription: string;
  readonly idealFor: string;
  readonly features: readonly string[];
  readonly visual: "headless" | "display" | "control";
  readonly displayTechnology: string;
  readonly integratedDisplay: boolean;
  readonly touch: boolean | "Configuration dependent";
  readonly controlBar: boolean;
  readonly rotaryControl: boolean;
  readonly haptics: boolean;
}

export const products = [
  {
    id: "homecloud-base",
    slug: "base",
    family: "base",
    displayName: brand.productFamilies.base,
    shortName: "Base",
    eyebrow: "The essential personal cloud",
    description: "Everything you need to bring files, backups and apps home.",
    longDescription:
      "A quiet, focused personal cloud managed through a clear Web UI. It is the direct way to start with local storage, useful apps and secure remote access.",
    idealFor: "A simple entry point for personal storage and everyday apps",
    features: [
      "Unified Web UI",
      "Personal storage and backup",
      "App ecosystem",
      "Secure remote access",
    ],
    visual: "headless",
    displayTechnology: "No integrated display",
    integratedDisplay: false,
    touch: false,
    controlBar: false,
    rotaryControl: false,
    haptics: false,
  },
  {
    id: "homecloud-plus",
    slug: "plus",
    family: "plus",
    displayName: brand.productFamilies.plus,
    shortName: "Plus",
    eyebrow: "Information at a glance",
    description: "The complete Base experience, with an integrated local display.",
    longDescription:
      "See storage, network, backup and system health without reaching for another screen. Display technology and local interaction can vary by configuration.",
    idealFor: "People who want visible device status and local interaction",
    features: [
      "Everything in Base",
      "Integrated display",
      "Glanceable device status",
      "Local controls",
    ],
    visual: "display",
    displayTechnology: "LCD or OLED, configuration dependent",
    integratedDisplay: true,
    touch: "Configuration dependent",
    controlBar: false,
    rotaryControl: false,
    haptics: false,
  },
  {
    id: "homecloud-pro",
    slug: "pro",
    family: "pro",
    displayName: brand.productFamilies.pro,
    shortName: "Pro",
    eyebrow: "The fullest local experience",
    description: "A richer hardware interface for a cloud that lives in the room.",
    longDescription:
      "An OLED main display, a distinct Control Bar, a rotary control and haptic feedback bring the software experience directly onto the hardware.",
    idealFor: "A premium, tactile hardware and software experience",
    features: [
      "Everything in Plus",
      "OLED main display",
      "Control Bar",
      "Rotary control and haptic feedback",
    ],
    visual: "control",
    displayTechnology: "OLED",
    integratedDisplay: true,
    touch: true,
    controlBar: true,
    rotaryControl: true,
    haptics: true,
  },
] as const satisfies readonly Product[];

export type ProductSlug = (typeof products)[number]["slug"];

export function getProduct(slug: string): Product | undefined {
  return products.find((product) => product.slug === slug);
}

export function getProductHref(product: Product): `/products/${ProductSlug}` {
  return `/products/${product.slug}` as `/products/${ProductSlug}`;
}
