import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { brand } from "@/config/brand";
import { getSiteUrl } from "@/config/site";

import "@/styles/globals.css";

export const metadata: Metadata = {
  metadataBase: getSiteUrl(),
  title: {
    default: `${brand.name} — ${brand.metadata.defaultTitle}`,
    template: `%s — ${brand.name}`,
  },
  description: brand.metadata.description,
  applicationName: brand.name,
  category: "technology",
  keywords: ["personal cloud", "home server", "private storage", "self-hosted apps", "backup"],
  authors: [{ name: brand.name }],
  creator: brand.name,
  publisher: brand.name,
  referrer: "origin-when-cross-origin",
  openGraph: {
    type: "website",
    siteName: brand.name,
    title: `${brand.name} — ${brand.metadata.defaultTitle}`,
    description: brand.metadata.description,
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: `${brand.name} — ${brand.metadata.defaultTitle}`,
    description: brand.metadata.description,
  },
};

export const viewport: Viewport = {
  colorScheme: "light dark",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f4f5f6" },
    { media: "(prefers-color-scheme: dark)", color: "#0e1013" },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">Skip to main content</a>
        <Header />
        <main id="main-content">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
