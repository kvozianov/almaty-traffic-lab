import Link from "next/link";
import { REPO_URL } from "./SiteHeader";

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <span>
          Almaty Traffic Lab · a model, not a forecast. Roads ©{" "}
          <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">
            OpenStreetMap contributors
          </a>
          , ODbL.
        </span>
        <span>
          <Link href="/methods">How it works</Link> · <a href={REPO_URL}>Source code</a> · Built by Kirill
        </span>
      </div>
    </footer>
  );
}
