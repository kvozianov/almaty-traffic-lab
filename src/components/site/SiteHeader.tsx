"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import BrandMark from "./BrandMark";

export const REPO_URL = "https://github.com/kvozianov/almaty-traffic-lab";

const links = [
  { href: "/lab", label: "Lab", short: "Lab" },
  { href: "/methods", label: "How it works", short: "Method" },
];

export default function SiteHeader({ wide = false }: { wide?: boolean }) {
  const pathname = usePathname();
  return (
    <header className={`site-header${wide ? " site-header-wide" : ""}`}>
      <div className="site-header-inner">
        <Link className="brand" href="/">
          <BrandMark />
          <span>Almaty Traffic Lab</span>
        </Link>
        <nav className="site-nav" aria-label="Main">
          {links.map((l) => (
            <Link key={l.href} href={l.href} aria-current={pathname === l.href ? "page" : undefined}>
              <span className="nav-long">{l.label}</span>
              <span className="nav-short">{l.short}</span>
            </Link>
          ))}
          <a href={REPO_URL} target="_blank" rel="noreferrer">
            <span className="nav-long">GitHub ↗</span>
            <span className="nav-short">Code ↗</span>
          </a>
        </nav>
      </div>
    </header>
  );
}
