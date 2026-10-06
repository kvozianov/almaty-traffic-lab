import Link from "next/link";

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <p>Abay Avenue case study · evidence level: proxy · road geometry: non-live real-data snapshot.</p>
        <Link href="/scenarios/abay-signal-retiming/dossier#methods">
          Methods and limitations
        </Link>
      </div>
    </footer>
  );
}
