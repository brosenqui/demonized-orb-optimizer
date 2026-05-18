import { Fragment } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { highestSetTierBonus } from "@/lib/setBonusData";

type StatRow = {
  name: string;
  shared: number;
  specific: number;
  total: number;
};

function normalize(value: number): number {
  return Number.isFinite(value) ? value : 0;
}

function formatNum(value: number): string {
  const normalized = normalize(value);
  if (Number.isInteger(normalized)) return normalized.toString();
  return Number(normalized.toFixed(4)).toString();
}

function formatTierBonus(setName: string, count: number): string | null {
  const highest = highestSetTierBonus(setName, count);
  if (!highest) return null;
  const parts = Object.entries(highest.bonusByStat)
    .filter(([, value]) => Number.isFinite(value))
    .map(([statName, value]) => `${statName} +${formatNum(value)}`);
  if (parts.length === 0) return null;
  return parts.join(", ");
}

function mergeRows(shared: Array<[string, number]>, specific: Array<[string, number]>): StatRow[] {
  const sharedMap = new Map(shared);
  const specificMap = new Map(specific);
  const keys = new Set<string>([...sharedMap.keys(), ...specificMap.keys()]);

  return [...keys]
    .map((name) => {
      const sharedValue = normalize(sharedMap.get(name) ?? 0);
      const specificValue = normalize(specificMap.get(name) ?? 0);
      return {
        name,
        shared: sharedValue,
        specific: specificValue,
        total: sharedValue + specificValue,
      };
    })
    .sort((left, right) => {
      if (right.total !== left.total) return right.total - left.total;
      if (right.shared !== left.shared) return right.shared - left.shared;
      if (right.specific !== left.specific) return right.specific - left.specific;
      return left.name.localeCompare(right.name);
    });
}

type LoadoutStatTablesProps = {
  sharedActiveSets: Array<[string, number]>;
  specificActiveSets: Array<[string, number]>;
  sharedTypeTotals: Array<[string, number]>;
  specificTypeTotals: Array<[string, number]>;
};

export default function LoadoutStatTables({
  sharedActiveSets,
  specificActiveSets,
  sharedTypeTotals,
  specificTypeTotals,
}: LoadoutStatTablesProps) {
  const activeSetRows = mergeRows(sharedActiveSets, specificActiveSets);
  const typeRows = mergeRows(sharedTypeTotals, specificTypeTotals);

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="rounded-2xl border bg-white/80 p-4 shadow-sm backdrop-blur">
        <div className="mb-2 text-lg font-semibold">Active Sets (Shared + Profile-only)</div>
        {activeSetRows.length === 0 ? (
          <p className="text-sm text-muted-foreground">No sets assigned.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-2/5">Set</TableHead>
                <TableHead className="w-1/5 text-right">Shared</TableHead>
                <TableHead className="w-1/5 text-right">Specific</TableHead>
                <TableHead className="w-1/5 text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {activeSetRows.map((row) => {
                const tierBonus = formatTierBonus(row.name, row.total);
                return (
                  <Fragment key={row.name}>
                    <TableRow>
                      <TableCell className="font-medium">{row.name}</TableCell>
                      <TableCell className="text-right font-mono">{formatNum(row.shared)}</TableCell>
                      <TableCell className="text-right font-mono">{formatNum(row.specific)}</TableCell>
                      <TableCell className="text-right font-mono">{formatNum(row.total)}</TableCell>
                    </TableRow>
                    {tierBonus && (
                      <TableRow className="bg-zinc-50/60">
                        <TableCell className="pl-8 text-xs text-zinc-500">↳ Set Bonus</TableCell>
                        <TableCell colSpan={3} className="text-xs font-mono text-zinc-700">
                          {tierBonus}
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                );
              })}
            </TableBody>
          </Table>
        )}
      </div>

      <div className="rounded-2xl border bg-white/80 p-4 shadow-sm backdrop-blur">
        <div className="mb-2 text-lg font-semibold">Totals by Type (Shared + Profile-only)</div>
        {typeRows.length === 0 ? (
          <p className="text-sm text-muted-foreground">No orb values to total.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-2/5">Type</TableHead>
                <TableHead className="w-1/5 text-right">Shared</TableHead>
                <TableHead className="w-1/5 text-right">Specific</TableHead>
                <TableHead className="w-1/5 text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {typeRows.map((row) => (
                <TableRow key={row.name}>
                  <TableCell className="font-medium">{row.name}</TableCell>
                  <TableCell className="text-right font-mono">{formatNum(row.shared)}</TableCell>
                  <TableCell className="text-right font-mono">{formatNum(row.specific)}</TableCell>
                  <TableCell className="text-right font-mono">{formatNum(row.total)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  );
}
