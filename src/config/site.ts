import { brand } from "@/config/brand";

const developmentUrl = "http://localhost:3000";

export function getSiteUrl(): URL {
  const configuredUrl = process.env.NEXT_PUBLIC_SITE_URL?.trim();

  if (!configuredUrl) {
    return new URL(developmentUrl);
  }

  try {
    return new URL(configuredUrl);
  } catch {
    return new URL(developmentUrl);
  }
}

export const siteNavigation = [
  { label: "Products", href: "/#products" },
  { label: `Why ${brand.name}`, href: "/#why" },
  { label: "Apps", href: "/apps" },
  { label: "Compare", href: "/compare" },
] as const;
