import React, { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from "@/components/ui/select";
import { rarityOptions, type OrbIn } from "@/lib/types";
import { ORB_TYPES, ORB_SETS } from "@/lib/orbData";
import { clampLevel, clampNonNegative } from "@/lib/rarityCaps";

/**
 * Controlled-from-parent: when rendered, it opens immediately and closes on Save/Cancel.
 */
export function AddOrbDialog({
  onAdd,
}: {
  onAdd: (orb: OrbIn) => void;
}) {
  const [open, setOpen] = useState(true);
  const [type, setType] = useState<string>(ORB_TYPES[0] ?? "");
  const [setName, setSetName] = useState<string>(ORB_SETS[0] ?? "");
  const [rarity, setRarity] = useState<string>("Rare");
  const [value, setValue] = useState<number>(0);
  const [level, setLevel] = useState<number>(1);

  function commit() {
    const final: OrbIn = {
      type,
      set: setName,
      rarity,
      value: clampNonNegative(value),
      level: clampLevel(rarity, level),
    };
    onAdd(final);
    setOpen(false);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader><DialogTitle>Add a new Orb</DialogTitle></DialogHeader>

        <div className="space-y-3">
          {/* Type */}
          <div>
            <label className="text-sm mb-1 block">Type</label>
            <Select value={type} onValueChange={setType}>
              <SelectTrigger><SelectValue placeholder="Select a type" /></SelectTrigger>
              <SelectContent>
                {ORB_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          {/* Set */}
          <div>
            <label className="text-sm mb-1 block">Set</label>
            <Select value={setName} onValueChange={setSetName}>
              <SelectTrigger><SelectValue placeholder="Select a set" /></SelectTrigger>
              <SelectContent>
                {ORB_SETS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          {/* Rarity */}
          <div>
            <label className="text-sm mb-1 block">Rarity</label>
            <Select value={rarity} onValueChange={(r) => {
              setRarity(r);
              // re-clamp level if rarity changes
              setLevel((prev) => clampLevel(r, prev));
            }}>
              <SelectTrigger><SelectValue placeholder="Select a rarity" /></SelectTrigger>
              <SelectContent>
                {rarityOptions.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>

          {/* Value + Level */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-sm mb-1 block">Value</label>
              <Input
                type="number"
                min={0}
                value={value}
                onChange={(e) => setValue(clampNonNegative(Number(e.target.value)))}
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

        <div className="flex justify-end gap-2 mt-4">
          <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={commit}>Save</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
