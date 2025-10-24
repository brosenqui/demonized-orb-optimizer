import React, { useMemo } from "react";
import OrbGrid from "../orbs/OrbGrid";
import type { OrbIn } from "@/lib/types";

// shadcn table
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import Section from "../ui/Section";

type Assignments = Record<string, OrbIn[]>;

function formatNum(n: number) {
  return Number.isFinite(n as number) ? Number((n as number).toFixed(4)) : n;
}

export default function ProfileResult({
  profileName,
  assignments,
}: {
  profileName: string;
  assignments: Assignments;
}) {
  const categories = Object.keys(assignments || {});

  // Flatten all assigned orbs for stats
  const allOrbs = useMemo(
    () => Object.values(assignments || {}).flat(),
    [assignments]
  );

  // --- Active sets (counts) ---
  const activeSets = useMemo(() => {
    const counts = new Map<string, number>();
    for (const o of allOrbs) {
      const key = o.set || "Unknown";
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    return Array.from(counts.entries()).sort(
      (a, b) => b[1] - a[1] || a[0].localeCompare(b[0])
    );
  }, [allOrbs]);

  // --- Totals by type (sum of value) ---
  const totalsByType = useMemo(() => {
    const totals: Record<string, number> = {};
    for (const o of allOrbs) {
      const t = o.type || "Unknown";
      const v = Number.isFinite(o.value) ? o.value : 0;
      totals[t] = (totals[t] ?? 0) + v;
    }
    return Object.entries(totals).sort((a, b) => b[1] - a[1]); // desc by total
  }, [allOrbs]);

  return (
    <Section title="">
      <div className="grid lg:grid-cols-12 gap-8">
        {/* LEFT: all categories + orb grids */}
        <div className="lg:col-span-8 space-y-8 pr-2">
          {categories.length === 0 ? (
            <p className="text-sm text-muted-foreground">No assignments.</p>
          ) : (
            categories.map((cat) => (
              <div key={cat}>
                <div className="mb-3 text-lg font-semibold">{cat}</div>
                <div className="p-3 sm:p-4 rounded-2xl bg-white/70 backdrop-blur border border-zinc-200 shadow-sm">
                  {/* Add slight scale and spacing bump for larger orb appearance */}
                  <div className="scale-[1.08] transform origin-top-left">
                    <OrbGrid
                      orbs={assignments[cat] || []}
                      density="comfortable"
                    />
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* RIGHT: details stacked vertically */}
        <aside className="lg:col-span-4 space-y-6 lg:sticky lg:top-20 self-start">
          {/* Active Sets */}
          <div className="rounded-2xl border bg-white/80 backdrop-blur p-4 shadow-sm">
            <div className="font-semibold mb-2 text-lg">Active Sets</div>
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
                      <TableCell className="text-right font-mono">
                        {count}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>

          {/* Totals by Type */}
          <div className="rounded-2xl border bg-white/80 backdrop-blur p-4 shadow-sm">
            <div className="font-semibold mb-2 text-lg">Totals by Type</div>
            {totalsByType.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No orb values to total.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-2/3">Type</TableHead>
                    <TableHead className="w-1/3 text-right">Total</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {totalsByType.map(([type, total]) => (
                    <TableRow key={type}>
                      <TableCell className="font-medium">{type}</TableCell>
                      <TableCell className="text-right font-mono">
                        {formatNum(total)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </aside>
      </div>
    </Section>
  );
}
