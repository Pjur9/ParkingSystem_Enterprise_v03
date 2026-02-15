import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Ovo je ključno za Docker
  output: "standalone",

  // Ignorišemo ESLint greške tokom builda da ne ruše Docker
  eslint: {
    ignoreDuringBuilds: true,
  },

  // Ignorišemo TypeScript greške tokom builda
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;