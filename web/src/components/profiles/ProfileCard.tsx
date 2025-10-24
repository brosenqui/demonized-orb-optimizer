import React from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "../ui/select";
import KvSelectTable from "../ui/KvSelectTable";
import { objectiveOptions, type OptimizeProfileIn, type Rarity } from "../../lib/types";
import { cn } from "../../lib/utils";

// rarity styles + mapping
const rarityBgClass: Record<Rarity, string> = {
  Rare: "bg-blue-100 text-blue-900",
  Epic: "bg-purple-100 text-purple-900",
  Legendary: "bg-amber-100 text-amber-900",
  Mythic: "bg-rose-100 text-rose-900",
};
const rarityRingClass: Record<Rarity, string> = {
  Rare: "ring-blue-300",
  Epic: "ring-purple-300",
  Legendary: "ring-amber-300",
  Mythic: "ring-rose-300",
};
const RARITIES: Rarity[] = ["Rare", "Epic", "Legendary", "Mythic"];
const CATEGORIES = ["Soul", "Wings", "Ego", "Beast", "Wagon"] as const;
const CLEAR_VALUE = "__none__" as const; // sentinel for clearing

type Props = {
  value: OptimizeProfileIn;
  onChange: (p: OptimizeProfileIn) => void;
  onRemove: () => void;
  availableSets: string[];
  availableTypes: string[];
  // NEW: bubble category changes to parent so it can propagate if shareable
  onSetCategory: (cat: string, rarity: Rarity | "") => void;
};

export default function ProfileCard({
  value,
  onChange,
  onRemove,
  availableSets,
  availableTypes,
  onSetCategory,
}: Props) {
  const categories = value.categories ?? {};

  return (
    <div className="rounded-2xl border p-4 space-y-4">
      {/* Header row: name + weight */}
      <div className="grid grid-cols-1 md:grid-cols-[1fr_160px] gap-3">
        <div className="space-y-1">
          <Label htmlFor={`profile-name-${value.name}`}>Profile name</Label>
          <Input
            id={`profile-name-${value.name}`}
            placeholder="Profile name"
            value={value.name}
            onChange={(e) => onChange({ ...value, name: e.target.value })}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor={`profile-weight-${value.name}`}>Weight</Label>
          <Input
            id={`profile-weight-${value.name}`}
            type="number"
            step="0.1"
            value={value.weight}
            onChange={(e) =>
              onChange({ ...value, weight: Number(e.target.value) })
            }
          />
        </div>
      </div>

      {/* Objective / Power / Epsilon */}
      <div className="grid md:grid-cols-3 gap-3">
        <div className="space-y-1">
          <Label>Objective</Label>
          <Select
            value={value.objective}
            onValueChange={(val) =>
              onChange({
                ...value,
                objective: val as OptimizeProfileIn["objective"],
              })
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Select objective" />
            </SelectTrigger>
            <SelectContent>
              {objectiveOptions.map((o) => (
                <SelectItem key={o} value={o}>
                  {o}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label htmlFor={`profile-power-${value.name}`}>Power</Label>
          <Input
            id={`profile-power-${value.name}`}
            type="number"
            step="0.1"
            value={value.power}
            onChange={(e) =>
              onChange({ ...value, power: Number(e.target.value) })
            }
          />
        </div>

        <div className="space-y-1">
          <Label htmlFor={`profile-eps-${value.name}`}>Epsilon</Label>
          <Input
            id={`profile-eps-${value.name}`}
            type="number"
            step="0.01"
            value={value.epsilon}
            onChange={(e) =>
              onChange({ ...value, epsilon: Number(e.target.value) })
            }
          />
        </div>
      </div>

      {/* Categories & Rarity (per profile) */}
      <div>
        <h4 className="font-medium mb-2">Categories & Rarity</h4>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {CATEGORIES.map((cat) => {
            const rarity = (categories[cat] as Rarity | undefined) || undefined;
            return (
              <div
                key={cat}
                className="flex items-center gap-3 rounded-xl border p-3"
              >
                <div className="w-24 text-sm font-medium">{cat}</div>
                <Select
                  value={rarity}
                  onValueChange={(val) => {
                    if (val === CLEAR_VALUE) {
                      onSetCategory(cat, "");
                    } else {
                      onSetCategory(cat, val as Rarity);
                    }
                  }}
                >
                  <SelectTrigger
                    className={cn(
                      "w-full ring-2",
                      rarity
                        ? `${rarityBgClass[rarity]} ${rarityRingClass[rarity]}`
                        : ""
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
                          {r}
                        </span>
                      </SelectItem>
                    ))}
                    {/* sentinel for clearing */}
                    <SelectItem value={CLEAR_VALUE}>None</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            );
          })}
        </div>
      </div>

      {/* Set Priority / Orb Weights / Orb Level Weights */}
      <div className="grid md:grid-cols-3 gap-4">
        <div>
          <h4 className="font-medium mb-1">Set Priority</h4>
          <KvSelectTable
            value={value.set_priority}
            onChange={(next) => onChange({ ...value, set_priority: next })}
            options={availableSets}
            labelKey="Set"
            labelVal="Priority"
            placeholderVal="1.0"
          />
        </div>

        <div>
          <h4 className="font-medium mb-1">Orb Weights</h4>
          <KvSelectTable
            value={value.orb_weights}
            onChange={(next) => onChange({ ...value, orb_weights: next })}
            options={availableTypes}
            labelKey="Orb Type"
            labelVal="Weight"
            placeholderVal="1.0"
          />
        </div>

        <div>
          <h4 className="font-medium mb-1">Orb Level Weights</h4>
          <KvSelectTable
            value={value.orb_level_weights}
            onChange={(next) =>
              onChange({ ...value, orb_level_weights: next })
            }
            options={availableTypes}
            labelKey="Orb Type"
            labelVal="Level Weight"
            placeholderVal="1.0"
          />
        </div>
      </div>

      <div className="text-right">
        <Button variant="destructive" onClick={onRemove}>
          Delete Profile
        </Button>
      </div>
    </div>
  );
}
