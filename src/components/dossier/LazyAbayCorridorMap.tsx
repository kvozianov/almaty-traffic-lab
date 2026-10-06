"use client";

import dynamic from "next/dynamic";

const AbayCorridorMap = dynamic(() => import("./AbayCorridorMap"), {
  ssr: false,
  loading: () => (
    <div
      className="flex h-full min-h-[320px] items-center justify-center bg-[#11110f] px-6 text-center text-sm text-stone-300 sm:min-h-[420px]"
      role="status"
      aria-live="polite"
    >
      Loading the non-live road-geometry context for this evidence dossier.
    </div>
  ),
});

export default AbayCorridorMap;
