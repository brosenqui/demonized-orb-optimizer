import React, { useMemo, useState } from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from "../ui/table";

type Props = {
  value: Record<string, number>;
  onChange: (next: Record<string, number>) => void;
  placeholderKey?: string;
  placeholderVal?: string;
};

export default function KvTable({
  value,
  onChange,
  placeholderKey = "key",
  placeholderVal = "1.0",
}: Props) {
  const [k, setK] = useState("");
  const [v, setV] = useState("");

  const entries = useMemo(
    () => Object.entries(value),
    [value]
  );

  function addPair() {
    const key = k.trim();
    const num = Number(v);
    if (!key || Number.isNaN(num)) return;
    onChange({ ...value, [key]: num });
    setK("");
    setV("");
  }

  function removeKey(key: string) {
    const next = Object.fromEntries(entries.filter(([kk]) => kk !== key));
    onChange(next);
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Input
          placeholder={placeholderKey}
          value={k}
          onChange={(e) => setK(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") addPair();
          }}
        />
        <Input
          placeholder={placeholderVal}
          value={v}
          inputMode="decimal"
          onChange={(e) => setV(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") addPair();
          }}
        />
        <Button onClick={addPair}>Add</Button>
      </div>

      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">No entries yet.</p>
      ) : (
        <div className="rounded-xl border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-1/2">Key</TableHead>
                <TableHead className="w-1/2">Value</TableHead>
                <TableHead className="w-24 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map(([key, val]) => (
                <TableRow key={key}>
                  <TableCell className="font-mono text-xs">{key}</TableCell>
                  <TableCell className="font-mono text-xs">{val}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => removeKey(key)}
                    >
                      Remove
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
