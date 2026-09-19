export const brand = {
  name: "HomeCloud",
  shortName: "HC",
  descriptor: "Personal cloud hardware and software",
  tagline: "Your digital life, where it belongs.",
  metadata: {
    defaultTitle: "Your personal cloud, at home",
    description:
      "A personal cloud for files, photos, backups and apps, built as one approachable home device.",
  },
  contact: {
    supportEmail: "support@example.com",
  },
  social: {
    x: "",
    instagram: "",
    github: "",
  },
  productFamilies: {
    base: "HomeCloud Base",
    plus: "HomeCloud Plus",
    pro: "HomeCloud Pro",
  },
} as const;

export type ProductFamilyKey = keyof typeof brand.productFamilies;
