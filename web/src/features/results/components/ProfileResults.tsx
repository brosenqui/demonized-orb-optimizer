import { useMemo } from "react";
import OrbGrid from "@/features/orbs/components/OrbGrid";
import LoadoutStatTables from "@/features/results/components/LoadoutStatTables";
import type { OrbIn } from "@/lib/types";
import {
  activeSetCounts,
  flattenAssignments,
  orderedCategories,
  totalsByType,
  type Assignments,
} from "@/features/results/utils/resultStats";

type ProfileResultsProps = {
  assignments: Assignments;
};

export default function ProfileResults({ assignments }: ProfileResultsProps) {
  const categories = useMemo(() => orderedCategories(assignments), [assignments]);
  const allOrbs = useMemo(() => flattenAssignments(assignments), [assignments]);
  const activeSets = useMemo(() => activeSetCounts(allOrbs), [allOrbs]);
  const typeTotals = useMemo(() => totalsByType(allOrbs), [allOrbs]);

  return (
    <div className="grid lg:grid-cols-12 gap-8">
      <div className="lg:col-span-8 space-y-8 pr-2">
        {categories.length === 0 ? (
          <p className="text-sm text-muted-foreground">No assignments.</p>
        ) : (
          categories.map((category) => (
            <div key={category}>
              <div className="mb-3 text-lg font-semibold">{category}</div>
              <div className="rounded-2xl border border-zinc-200 bg-white/70 p-3 shadow-sm backdrop-blur sm:p-4">
                <OrbGrid
                  orbs={assignments[category] ?? ([] as OrbIn[])}
                  density="comfortable"
                />
              </div>
            </div>
          ))
        )}
      </div>

      <aside className="self-start space-y-6 lg:sticky lg:top-20 lg:col-span-4">
        <LoadoutStatTables activeSets={activeSets} typeTotals={typeTotals} />
      </aside>
    </div>
  );
}
