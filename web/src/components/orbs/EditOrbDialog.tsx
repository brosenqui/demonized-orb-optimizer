import React, { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from "@/components/ui/select";
import { rarityOptions, type OrbIn } from "@/lib/types";
import { ORB_TYPES, ORB_SETS } from "@/lib/orbData";
import { clampLevel, clampNonNegative } from "@/lib/rarityCaps";

export function EditOrbDialog({
  open,
  onOpenChange,
  value,
  onSave,
  onDelete,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  value: OrbIn;
  onSave: (next: OrbIn) => void;
  onDelete: () => void;
}) {
  const [type, setType] = useState<string>(value.type);
  const [setName, setSetName] = useState<string>(value.set);
  const [rarity, setRarity] = useState<string>(value.rarity);
  const [val, setVal] = useState<number>(value.value);
  const [level, setLevel] = useState<number>(value.level);

  useEffect(() => {
    setType(value.type);
    setSetName(value.set);
    setRarity(value.rarity);
    setVal(value.value);
    setLevel(value.level);
  }, [value]);

  function commit() {
    onSave({
      type,
      set: setName,
      rarity,
      value: clampNonNegative(val),
      level: clampLevel(rarity, level),
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader><DialogTitle>Edit Orb</DialogTitle></DialogHeader>

        <div className="space-y-3">
          <div>
            <label className="text-sm mb-1 block">Type</label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger><SelectValue placeholder="Select a type" /></SelectTrigger>
              <SelectContent>
                {ORB_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm mb-1 block">Set</label>
            <Select value={setName} onValueChange={setSetName}>
              <SelectTrigger><SelectValue placeholder="Select a set" /></SelectTrigger>
              <SelectContent>
                {ORB_SETS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm mb-1 block">Rarity</label>
            <Select value={rarity} onValueChange={(r) => {
              setRarity(r);
              setLevel((prev) => clampLevel(r, prev));
            }}>
              <SelectTrigger><SelectValue placeholder="Select a rarity" /></SelectTrigger>
              <SelectContent>
                {rarityOptions.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-sm mb-1 block">Value</label>
              <Input
                type="number"
                min={0}
                value={val}
                onChange={(e) => setVal(clampNonNegative(Number(e.target.value)))}
              />
            </div>
            <div>
              <label className="text-sm mb-1 block">Level</label>
              <Input
                type="number"
                min={0}
                max={clampLevel(rarity, Infinity)}
                value={level}
                onChange={(e) => setLevel(clampLevel(rarity, Number(e.target.value)))}
              />
              <p className="text-xs text-zinc-500 mt-1">Max: {clampLevel(rarity, Infinity)}</p>
            </div>
          </div>
        </div>

        <div className="flex justify-between mt-4">
          <Button variant="destructive" onClick={onDelete}>Delete</Button>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button onClick={commit}>Save</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
