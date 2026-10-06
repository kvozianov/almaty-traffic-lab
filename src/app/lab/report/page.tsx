import { Suspense } from "react";
import type { Metadata } from "next";
import Report from "@/components/lab/Report";
import SiteFooter from "@/components/site/SiteFooter";
import SiteHeader from "@/components/site/SiteHeader";

export const metadata: Metadata = {
  title: "Scenario report",
  description: "A reproducible report of one Almaty Traffic Lab scenario.",
};

export default function ReportPage() {
  return (
    <>
      <SiteHeader />
      <main id="main-content" className="page">
        <Suspense fallback={null}>
          <Report />
        </Suspense>
      </main>
      <SiteFooter />
    </>
  );
}
