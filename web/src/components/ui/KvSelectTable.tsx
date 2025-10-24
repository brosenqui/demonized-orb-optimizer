import React, { useMemo, useState } from "react";
import { Button } from "./button";
import { Input } from "./input";
import {
  Table, TableHeader, TableRow, TableHead, TableBody, TableCell,
} from "./table";
import {
  Select, SelectTrigger, SelectContent, SelectItem, SelectValue,
} from "./select";
import { cn } from "../../lib/utils";

type Props = {
  value: Record<string, number>;
  onChange: (next: Record<string, number>) => void;
  options: string[];           // available keys (sets or types)
  labelKey?: string;
  labelVal?: string;
  placeholderVal?: string;
};

export default function KvSelectTable({
  value,
  onChange,
  options,
  labelKey = "Key",
  labelVal = "Value",
  placeholderVal = "1.0",
}: Props) {
  const [selectedKey, setSelectedKey] = useState<string>("");
  const [val, setVal] = useState<string>("");

  const entries = useMemo(() => Object.entries(value), [value]);

  const remainingOptions = useMemo(() => {
    const used = new Set(Object.keys(value));
    return options.filter((o) => !used.has(o));
  }, [options, value]);

  function addPair() {
    const key = selectedKey.trim();
    const num = Number(val);
    if (!key || Number.isNaN(num)) return;
    onChange({ ...value, [key]: num });
    setSelectedKey("");
    setVal("");
  }

  function removeKey(key: string) {
    const next = Object.fromEntries(entries.filter(([k]) => k !== key));
    onChange(next);
  }

  function updateValue(key: string, raw: string) {
    const num = Number(raw);
    if (Number.isNaN(num)) return;
    onChange({ ...value, [key]: num });
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-[1fr_1fr_auto] gap-2">
        <Select value={selectedKey} onValueChange={setSelectedKey}>
          <SelectTrigger className={cn("w-full")}>
            <SelectValue placeholder={labelKey} />
          </SelectTrigger>
          <SelectContent>
            {remainingOptions.length === 0 && (
              <div className="px-2 py-1 text-sm text-muted-foreground">No keys available</div>
            )}
            {remainingOptions.map((opt) => (
              <SelectItem key={opt} value={opt}>{opt}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Input
          placeholder={placeholderVal}
          value={val}
          inputMode="decimal"
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && addPair()}
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
                <TableHead className="w-1/2">{labelKey}</TableHead>
                <TableHead className="w-1/2">{labelVal}</TableHead>
                <TableHead className="w-24 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entries.map(([k, v]) => (
                <TableRow key={k}>
                  <TableCell className="font-mono text-xs">{k}</TableCell>
                  <TableCell>
                    <Input
                      value={String(v)}
                      inputMode="decimal"
                      onChange={(e) => updateValue(k, e.target.value)}
                    />
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="destructive" size="sm" onClick={() => removeKey(k)}>
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
