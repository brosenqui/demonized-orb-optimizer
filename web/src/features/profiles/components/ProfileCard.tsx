import React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import KvSelectTable from "@/components/ui/KvSelectTable";
import {
  objectiveOptions,
  type CategoryRarity,
  type OptimizeProfileIn,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { HelpTooltip } from "@/components/ui/helpToolTip";
import { CATEGORIES } from "@/lib/categoryData";

// rarity styles + mapping
const rarityBgClass: Record<CategoryRarity, string> = {
  Rare: "bg-blue-100 text-blue-900",
  Epic: "bg-purple-100 text-purple-900",
  Legendary: "bg-amber-100 text-amber-900",
  Mythic: "bg-rose-100 text-rose-900",
};
const rarityRingClass: Record<CategoryRarity, string> = {
  Rare: "ring-blue-300",
  Epic: "ring-purple-300",
  Legendary: "ring-amber-300",
  Mythic: "ring-rose-300",
};
const RARITIES: CategoryRarity[] = ["Rare", "Epic", "Legendary", "Mythic"];
const CLEAR_VALUE = "__none__" as const; // sentinel for clearing

type Props = {
  value: OptimizeProfileIn;
  onChange: (p: OptimizeProfileIn) => void;
  onRemove: () => void;
  availableSets: readonly string[];
  availableTypes: readonly string[];
  // Bubble category changes to parent so it can propagate within matrix-enabled profiles.
  onSetCategory: (cat: string, rarity: CategoryRarity | "") => void;
};

export default function ProfileCard({
  value,
  onChange,
  onRemove,
  availableSets,
  availableTypes,
  onSetCategory,
}: Props) {
  const idPrefix = React.useId();
  const categories = value.categories ?? {};

  return (
    <div className="rounded-2xl border p-4 space-y-4">
      {/* Header row: name + weight */}
      <div className="grid grid-cols-1 md:grid-cols-[1fr_160px] gap-3">
        <div className="space-y-1">
          {/* group label + tooltip */}
          <div className="flex items-center gap-2">
            <Label htmlFor={`${idPrefix}-profile-name`}>Profile name</Label>
            <HelpTooltip text="A descriptive name for this optimization profile." />
          </div>

          <Input
            id={`${idPrefix}-profile-name`}
            placeholder="Profile name"
            value={value.name}
            onChange={(e) => onChange({ ...value, name: e.target.value })}
          />
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Label htmlFor={`${idPrefix}-profile-weight`}>Weight</Label>
            <HelpTooltip text="The relative importance of this profile when optimizing. Higher weight means the optimizer will prioritize this profile's objectives more." />
          </div>
          <Input
            id={`${idPrefix}-profile-weight`}
            type="number"
            step="0.1"
            value={value.weight}
            onChange={(e) =>
              onChange({ ...value, weight: Number(e.target.value) || 0 })
            }
          />
        </div>
      </div>

      {/* Objective / Power / Epsilon */}
      <div className="grid md:grid-cols-3 gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Label>Objective</Label>
            <HelpTooltip text="The main goal of this profile during optimization. Choose an objective that aligns with your desired outcome for orb selection." />
          </div>
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
          <div className="flex items-center gap-2">
            <Label htmlFor={`${idPrefix}-profile-power`}>Power</Label>
            <HelpTooltip text="Determines how strongly this profile's objective influences orb selection. A higher power value increases the emphasis on this profile's goals during optimization." />
          </div>
          <Input
            id={`${idPrefix}-profile-power`}
            type="number"
            step="0.1"
            value={value.power}
            onChange={(e) =>
              onChange({ ...value, power: Number(e.target.value) || 0 })
            }
          />
        </div>

        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Label htmlFor={`${idPrefix}-profile-eps`}>Epsilon</Label>
            <HelpTooltip text="A small tolerance value that helps prevent overfitting to this profile's objectives. It allows for some flexibility in orb selection, ensuring a more balanced optimization." />
          </div>
          <Input
            id={`${idPrefix}-profile-eps`}
            type="number"
            step="0.01"
            value={value.epsilon}
            onChange={(e) =>
              onChange({ ...value, epsilon: Number(e.target.value) || 0 })
            }
          />
        </div>
      </div>

      {/* Categories & Rarity (per profile) */}
      <div>
        <h4 className="font-medium mb-2">Categories & Rarity</h4>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {CATEGORIES.map((cat) => {
            const rarity = categories[cat];
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
                      onSetCategory(cat, val as CategoryRarity);
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
          <div className="flex items-center gap-2">
            <h4 className="font-medium mb-1">Set Priority</h4>
            <HelpTooltip text="Assign priority levels to different orb sets for this profile. Higher priority sets will be favored during optimization, influencing the selection of orbs based on your preferences." />
          </div>
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
          <div className="flex items-center gap-2">
            <h4 className="font-medium mb-1">Orb Weights</h4>
            <HelpTooltip text="Define weights for different orb types for this profile. Higher weights increase the likelihood of selecting those orb types during optimization, allowing you to tailor the orb selection process to your strategy." />
          </div>
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
          <div className="flex items-center gap-2">
            <h4 className="font-medium mb-1">Orb Level Weights</h4>
            <HelpTooltip text="Set weights for different orb levels for this profile. Higher level weights will influence the optimizer to favor orbs with higher levels during selection, helping you achieve your desired orb distribution." />
          </div>
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
