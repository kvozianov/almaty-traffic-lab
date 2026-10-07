import { Suspense } from "react";
import type { Metadata } from "next";
import LabApp from "@/components/lab/LabApp";
import SiteHeader from "@/components/site/SiteHeader";

export const metadata: Metadata = {
  title: "Lab",
  description: "Pick a street in Almaty, change it, and watch the morning rush find new routes.",
};

export default function LabPage() {
  return (
    <>
      <SiteHeader wide />
      <main id="main-content">
        <Suspense fallback={null}>
          <LabApp />
        </Suspense>
      </main>
    </>
  );
}
