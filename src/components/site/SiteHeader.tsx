"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  { href: "/scenarios/abay-signal-retiming/dossier", label: "Case dossier" },
  { href: "/scenarios/abay-signal-retiming/dossier#methods", label: "Methods" },
  { href: "/sandbox", label: "Demo sandbox" },
];

export default function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="site-header">
      <nav className="site-nav" aria-label="Primary navigation">
        <Link className="site-brand" href="/scenarios/abay-signal-retiming/dossier">
          <span className="site-brand-mark" aria-hidden="true">A</span>
          <span className="site-brand-copy">
            <strong>Almaty Mobility</strong>
            <span>Evidence dossier</span>
          </span>
        </Link>
        <div className="site-nav-links">
          {navigation.map((item) => {
            const active = item.href.startsWith("/sandbox") ? pathname === "/sandbox" : item.href.includes("#") ? false : pathname.startsWith("/scenarios");
            return (
              <Link
                aria-current={active ? "page" : undefined}
                className="site-nav-link"
                href={item.href}
                key={item.href}
              >
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </header>
  );
}
