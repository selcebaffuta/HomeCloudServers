import type { Metadata } from "next";

import { brand } from "@/config/brand";
import { getSiteUrl } from "@/config/site";

interface MetadataInput {
  readonly title: string;
  readonly description: string;
  readonly path: string;
}

export function createMetadata({ title, description, path }: MetadataInput): Metadata {
  const canonical = new URL(path, getSiteUrl());

  return {
    title,
    description,
    alternates: { canonical },
    openGraph: {
      title,
      description,
      url: canonical,
      siteName: brand.name,
      type: "website",
      locale: "en_US",
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
  };
}
