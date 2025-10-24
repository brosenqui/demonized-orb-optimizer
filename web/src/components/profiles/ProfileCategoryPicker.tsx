import React, { useMemo } from "react";
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from "@/components/ui/select";
import { CATEGORIES, CATEGORY_RARITY_CHOICES, slotsForRarity } from "@/lib/categoryData";

export type CatRarity = Record<string, (typeof CATEGORY_RARITY_CHOICES)[number]>;

export default function ProfileCategoryPicker({
  value,
  onChange,
}: {
  value: CatRarity;
  onChange: (next: CatRarity) => void;
}) {
  const totalSlots = useMemo(
    () => CATEGORIES.reduce((sum, c) => sum + slotsForRarity(value[c] || "Rare"), 0),
    [value]
  );

  return (
    <div className="rounded-2xl border p-3 bg-white/60">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-medium">Categories</h4>
        <div className="text-xs text-zinc-500">Total slots: <span className="font-mono">{totalSlots}</span></div>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {CATEGORIES.map((cat) => {
          const rarity = (value[cat] as any) || "Rare";
          return (
            <div key={cat} className="rounded-xl border p-2">
              <div className="flex items-center justify-between mb-1">
                <div className="font-semibold">{cat}</div>
                <div className="text-[11px] text-zinc-500">
                  Slots: <span className="font-mono">{slotsForRarity(rarity)}</span>
                </div>
              </div>
              <Select
                value={rarity}
                onValueChange={(r) => onChange({ ...value, [cat]: r as any })}
              >
                <SelectTrigger><SelectValue placeholder="Select rarity" /></SelectTrigger>
                <SelectContent>
                  {CATEGORY_RARITY_CHOICES.map((r) => (
                    <SelectItem key={r} value={r}>{r}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          );
        })}
      </div>
    </div>
  );
}
