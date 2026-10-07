const configuredSupportEmail = process.env.NEXT_PUBLIC_SUPPORT_EMAIL?.trim() || null;
const name = "HomeCloud";

export const brand = {
  name,
  shortName: "HC",
  localHostname: "homecloud.local",
  descriptor: "Personal cloud hardware and software",
  tagline: "Your digital life, where it belongs.",
  metadata: {
    defaultTitle: "Your personal cloud, at home",
    description:
      "A personal cloud for files, photos, backups and apps, built as one approachable home device.",
  },
  contact: {
    supportEmail: configuredSupportEmail,
  },
  social: {
    x: "",
    instagram: "",
    github: "",
  },
  productFamilies: {
    base: `${name} Base`,
    plus: `${name} Plus`,
    pro: `${name} Pro`,
  },
} as const;

export type ProductFamilyKey = keyof typeof brand.productFamilies;
