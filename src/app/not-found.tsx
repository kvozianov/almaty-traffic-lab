import Link from "next/link";
import SiteFooter from "@/components/site/SiteFooter";
import SiteHeader from "@/components/site/SiteHeader";

export default function NotFound() {
  return (
    <>
      <SiteHeader />
      <main id="main-content" className="page" style={{ padding: "96px var(--gutter) 128px" }}>
        <p className="label">404</p>
        <h1 className="title" style={{ marginTop: 12 }}>This street isn’t on our map.</h1>
        <p className="body" style={{ marginTop: 8 }}>The page you opened does not exist.</p>
        <Link className="btn btn-primary" href="/lab" style={{ marginTop: 24 }}>
          Open the lab
        </Link>
      </main>
      <SiteFooter />
    </>
  );
}
