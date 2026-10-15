import type { Metadata } from "next";
import { ComingSoon } from "@/components/coming-soon";

export const metadata: Metadata = { title: "Plan" };

export default function PlanPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-2xl font-bold">Plan</h1>
      <ComingSoon title="Coming in Phase 1">This section is part of the MVP build.</ComingSoon>
    </div>
  );
}
