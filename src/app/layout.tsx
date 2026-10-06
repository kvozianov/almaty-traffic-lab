import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";
import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, Instrument_Sans } from "next/font/google";

const sans = Instrument_Sans({ subsets: ["latin"], variable: "--font-instrument", display: "swap" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-plex-mono", display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: {
    default: "Almaty Traffic Lab",
    template: "%s · Almaty Traffic Lab",
  },
  description:
    "Pick any street in Almaty, change it, and see how city traffic redistributes. A traffic-assignment model that runs in your browser.",
  icons: {
    icon: {
      type: "image/svg+xml",
      url: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%23141413'/%3E%3Cpath d='M6 20h20M12 6v20' stroke='%23f6f5f1' stroke-width='3' stroke-linecap='round'/%3E%3Ccircle cx='12' cy='20' r='3.5' fill='%23c4442b'/%3E%3C/svg%3E",
    },
  },
};

export const viewport: Viewport = {
  themeColor: "#f6f5f1",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${sans.variable} ${mono.variable}`}>
      <body>
        <a className="skip-link" href="#main-content">
          Skip to main content
        </a>
        {children}
      </body>
    </html>
  );
}
