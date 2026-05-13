import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

function formatNum(value: number): number {
  return Number((Number.isFinite(value) ? value : 0).toFixed(4));
}

type LoadoutStatTablesProps = {
  activeSets: Array<[string, number]>;
  typeTotals: Array<[string, number]>;
  activeSetsTitle?: string;
  typeTotalsTitle?: string;
  layout?: "stacked" | "columns";
};

export default function LoadoutStatTables({
  activeSets,
  typeTotals,
  activeSetsTitle = "Active Sets",
  typeTotalsTitle = "Totals by Type",
  layout = "stacked",
}: LoadoutStatTablesProps) {
  return (
    <div className={layout === "columns" ? "grid gap-4 md:grid-cols-2" : "space-y-6"}>
      <div className="rounded-2xl border bg-white/80 p-4 shadow-sm backdrop-blur">
        <div className="mb-2 text-lg font-semibold">{activeSetsTitle}</div>
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
        <div className="mb-2 text-lg font-semibold">{typeTotalsTitle}</div>
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
    </div>
  );
}
