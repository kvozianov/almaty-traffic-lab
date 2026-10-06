import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  async redirects() {
    return [
      {
        source: "/",
        destination: "/scenarios/abay-signal-retiming/dossier",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
