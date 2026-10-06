import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";
import type { Metadata } from "next";
import SiteFooter from "@/components/site/SiteFooter";
import SiteHeader from "@/components/site/SiteHeader";

export const metadata: Metadata = {
  title: {
    default: "Almaty Mobility Decision Platform",
    template: "%s · Almaty Mobility Decision Platform",
  },
  description:
    "An evidence-gated university case study of signal retiming on Abay Avenue, Almaty.",
  icons: {
    icon: {
      type: "image/svg+xml",
      url: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%231d221f'/%3E%3Cpath d='M8 24 15.5 7h2L25 24h-4l-1.5-4H13L11.5 24Z' fill='%23a9b9ad'/%3E%3Cpath d='M14.4 16.5h3.8l-1.9-5.4Z' fill='%231d221f'/%3E%3C/svg%3E",
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">
          Skip to main content
        </a>
        <SiteHeader />
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
