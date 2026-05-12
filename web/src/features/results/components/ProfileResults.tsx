import { useMemo } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import OrbGrid from "@/features/orbs/components/OrbGrid";
import type { OrbIn } from "@/lib/types";
import {
  activeSetCounts,
  flattenAssignments,
  orderedCategories,
  totalsByType,
  type Assignments,
} from "@/features/results/utils/resultStats";

function formatNum(value: number): number {
  return Number((Number.isFinite(value) ? value : 0).toFixed(4));
}

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
        <div className="rounded-2xl border bg-white/80 p-4 shadow-sm backdrop-blur">
          <div className="mb-2 text-lg font-semibold">Active Sets</div>
          {activeSets.length === 0 ? (
            <p className="text-sm text-muted-foreground">No sets assigned.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-2/3">Set</TableHead>
                  <TableHead className="w-1/3 text-right">Count</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {activeSets.map(([setName, count]) => (
                  <TableRow key={setName}>
                    <TableCell className="font-medium">{setName}</TableCell>
                    <TableCell className="text-right font-mono">{count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>

        <div className="rounded-2xl border bg-white/80 p-4 shadow-sm backdrop-blur">
          <div className="mb-2 text-lg font-semibold">Totals by Type</div>
          {typeTotals.length === 0 ? (
            <p className="text-sm text-muted-foreground">No orb values to total.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-2/3">Type</TableHead>
                  <TableHead className="w-1/3 text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {typeTotals.map(([type, total]) => (
                  <TableRow key={type}>
                    <TableCell className="font-medium">{type}</TableCell>
                    <TableCell className="text-right font-mono">{formatNum(total)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </aside>
    </div>
  );
}
