import type { MetadataRoute } from "next";

import { brand } from "@/config/brand";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: brand.name,
    short_name: brand.shortName,
    description: brand.metadata.description,
    start_url: "/",
    display: "standalone",
    background_color: "#f4f5f6",
    theme_color: "#f4f5f6",
  };
}
