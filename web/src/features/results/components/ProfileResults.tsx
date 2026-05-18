import { useMemo } from "react";
import OrbGrid from "@/features/orbs/components/OrbGrid";
import {
  orderedCategories,
  type Assignments,
} from "@/features/results/utils/resultStats";

type ProfileResultsProps = {
  assignments: Assignments;
};

export default function ProfileResults({ assignments }: ProfileResultsProps) {
  const categories = useMemo(() => orderedCategories(assignments), [assignments]);

  return (
    <div className="space-y-6">
      {categories.length === 0 ? (
        <p className="text-sm text-muted-foreground">No assignments.</p>
      ) : (
        categories.map((category) => (
          <div key={category}>
            <div className="mb-3 text-lg font-semibold">{category}</div>
            <div className="rounded-2xl border border-zinc-200 bg-white/70 p-3 shadow-sm backdrop-blur sm:p-4">
              <OrbGrid
                orbs={assignments[category] ?? []}
                density="comfortable"
              />
            </div>
          </div>
        ))
      )}
    </div>
  );
}
