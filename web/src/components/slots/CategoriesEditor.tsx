import React, { useMemo } from "react";
import Section from "../ui/Section";
import { Button } from "../ui/button";
import {
  Select, SelectTrigger, SelectContent, SelectItem, SelectValue,
} from "../ui/select";
import { rarityBgClass, rarityRingClass, rarityToSlots, type Rarity } from "../../lib/colors";
import { cn } from "../../lib/utils";

const CATEGORIES = ["Soul", "Wings", "Ego", "Beast", "Wagon"] as const;
const RARITIES: Rarity[] = ["Rare", "Epic", "Legendary", "Mythic"];

type Props = {
  // slots map is the API contract: { category: slotsCount }
  slots: Record<string, number>;
  setSlots: (s: Record<string, number>) => void;
};

export default function CategoriesEditor({ slots, setSlots }: Props) {
  // Convert slots -> rarity for UI (best-effort inverse)
  const selected: Record<string, Rarity | ""> = useMemo(() => {
    const out: Record<string, Rarity | ""> = {};
    for (const c of CATEGORIES) {
      const n = Number(slots[c] ?? 0);
      const rarity =
        (Object.entries(rarityToSlots).find(([_, v]) => v === n)?.[0] as Rarity | undefined) || "";
      out[c] = rarity;
    }
    return out;
  }, [slots]);

  function setCategoryRarity(cat: string, rarity: Rarity | "") {
    const next = { ...slots };
    if (!rarity) {
      delete next[cat];
    } else {
      next[cat] = rarityToSlots[rarity];
    }
    setSlots(next);
  }

  function clearAll() {
    setSlots({});
  }

  return (
    <Section
      title="Categories & Rarity"
      actions={
        <div className="flex gap-2">
          <Button variant="destructive" onClick={clearAll}>Clear</Button>
        </div>
      }
    >
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {CATEGORIES.map((cat) => {
          const rarity = selected[cat] || "";
          return (
            <div key={cat} className="flex items-center gap-3 rounded-xl border p-3">
              <div className="w-24 text-sm font-medium">{cat}</div>
              <Select
                value={rarity}
                onValueChange={(val) => setCategoryRarity(cat, val as Rarity)}
              >
                <SelectTrigger
                  className={cn(
                    "w-full ring-2",
                    rarity ? `${rarityBgClass[rarity as Rarity]} ${rarityRingClass[rarity as Rarity]}` : ""
                  )}
                >
                  <SelectValue placeholder="Select rarity" />
                </SelectTrigger>
                <SelectContent>
                  {RARITIES.map((r) => (
                    <SelectItem key={r} value={r}>
                      <span
                        className={cn(
                          "inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium",
                          rarityBgClass[r]
                        )}
                      >
                        {r} &nbsp; · &nbsp; {rarityToSlots[r]} slot{rarityToSlots[r] === 1 ? "" : "s"}
                      </span>
                    </SelectItem>
                  ))}
                  <SelectItem value={"" as unknown as string}>None</SelectItem>
                </SelectContent>
              </Select>
            </div>
          );
        })}
      </div>
    </Section>
  );
}
