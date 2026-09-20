import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  // Next 16 enables the subprocess-based checker by default. In this build
  // environment its stdout can be lost before --showConfig is parsed; the
  // pinned TypeScript 5 compiler API is available and avoids that race.
  experimental: {
    useTypeScriptCli: false,
  },
  images: {
    formats: ["image/avif", "image/webp"],
  },
};

export default nextConfig;
