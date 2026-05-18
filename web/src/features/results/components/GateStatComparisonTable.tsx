import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { HelpTooltip } from "@/components/ui/helpToolTip";

type GateStatRow = {
  stat: string;
  shared: number;
  specific: number;
  total: number;
};

type GateStatComparisonTableProps = {
  sharedStats: Array<[string, number]>;
  specificStats: Array<[string, number]>;
};

function normalize(value: number): number {
  return Number.isFinite(value) ? value : 0;
}

function formatNum(value: number): string {
  const normalized = normalize(value);
  if (Number.isInteger(normalized)) return normalized.toString();
  return Number(normalized.toFixed(4)).toString();
}

function mergeRows(shared: Array<[string, number]>, specific: Array<[string, number]>): GateStatRow[] {
  const sharedMap = new Map(shared);
  const specificMap = new Map(specific);
  const stats = new Set<string>([...sharedMap.keys(), ...specificMap.keys()]);

  return [...stats]
    .map((stat) => {
      const sharedValue = normalize(sharedMap.get(stat) ?? 0);
      const specificValue = normalize(specificMap.get(stat) ?? 0);
      return {
        stat,
        shared: sharedValue,
        specific: specificValue,
        total: sharedValue + specificValue,
      };
    })
    .sort((left, right) => right.total - left.total || left.stat.localeCompare(right.stat));
}

export default function GateStatComparisonTable({
  sharedStats,
  specificStats,
}: GateStatComparisonTableProps) {
  const rows = mergeRows(sharedStats, specificStats);

  return (
    <div className="rounded-2xl border bg-white/80 p-4 shadow-sm backdrop-blur">
      <div className="mb-2 flex items-center gap-1 text-lg font-semibold">
        <span>Orb Level Stats (Shared + Profile-only)</span>
        <HelpTooltip text="Type-specific bonuses unlocked at orb levels 3, 6, and 9 (cumulative), split by shared vs profile-only assignments." />
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">No level-gate stats contributed.</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-2/5">Stat</TableHead>
              <TableHead className="w-1/5 text-right">Shared</TableHead>
              <TableHead className="w-1/5 text-right">Specific</TableHead>
              <TableHead className="w-1/5 text-right">Total</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.stat}>
                <TableCell className="font-medium">{row.stat}</TableCell>
                <TableCell className="text-right font-mono">{formatNum(row.shared)}</TableCell>
                <TableCell className="text-right font-mono">{formatNum(row.specific)}</TableCell>
                <TableCell className="text-right font-mono">{formatNum(row.total)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
