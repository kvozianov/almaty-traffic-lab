import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    default: "Лаборатория транспортных решений Алматы",
    template: "%s · Транспортная лаборатория Алматы",
  },
  description:
    "Университетский проект: воспроизводимое досье транспортного сценария для проспекта Абая.",
  icons: {
    icon: {
      type: "image/svg+xml",
      url: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%23181814'/%3E%3Cpath d='M8 24 15.5 7h2L25 24h-4l-1.5-4H13L11.5 24Z' fill='%23f59e2e'/%3E%3Cpath d='M14.4 16.5h3.8l-1.9-5.4Z' fill='%23181814'/%3E%3C/svg%3E",
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
