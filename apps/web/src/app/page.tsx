import { ComingSoon } from "@/components/coming-soon";

const MACROS = [
  { label: "Protein", color: "bg-protein" },
  { label: "Carbs", color: "bg-carbs" },
  { label: "Fat", color: "bg-fat" },
  { label: "Fibre", color: "bg-fibre" },
];

export default function TodayPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="text-sm text-muted">Today</p>
        <h1 className="font-display text-3xl font-bold tracking-tight">Every meal is a rep.</h1>
      </div>

      <section aria-label="Macro budget" className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {MACROS.map((m) => (
          <div key={m.label} className="rounded-lg border border-border bg-surface p-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <span aria-hidden className={`size-2.5 rounded-full ${m.color}`} />
              {m.label}
            </div>
            <p className="mt-2 font-display text-2xl font-semibold">—</p>
            <p className="text-xs text-muted">Targets arrive in Phase 1</p>
          </div>
        ))}
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <ComingSoon title="Meals logged">
          Log from WhatsApp with a photo, a voice note or text. Entries will appear here.
        </ComingSoon>
        <ComingSoon title="What should I cook?">
          Suggestions that fit your pantry, utensils, time and remaining macros.
        </ComingSoon>
      </div>
    </div>
  );
}
