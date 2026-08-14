import type { SchemeSummary } from "@/types";
import { SchemeCard } from "@/features/schemes/components/SchemeCard";

interface SchemeGridProps {
  schemes: SchemeSummary[];
}

/** Responsive grid of scheme cards. */
export function SchemeGrid({ schemes }: SchemeGridProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {schemes.map((scheme) => (
        <SchemeCard key={scheme.id} scheme={scheme} />
      ))}
    </div>
  );
}
