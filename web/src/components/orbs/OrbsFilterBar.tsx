import * as React from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";

type Props = {
  allTypes: string[];
  allSets: string[];
  allRarities: string[];
  selectedTypes: string[];
  setSelectedTypes: (v: string[]) => void;
  selectedSets: string[];
  setSelectedSets: (v: string[]) => void;
  selectedRarities: string[];
  setSelectedRarities: (v: string[]) => void;
  levelMin: number;
  levelMax: number;
  setLevelMin: (v: number) => void;
  setLevelMax: (v: number) => void;
  searchQuery: string;
  setSearchQuery: (v: string) => void;
  className?: string;
};

type ToggleGroupProps = {
  label: string;
  options: string[];
  selected: string[];
  setSelected: (values: string[]) => void;
  allTitle: string;
};

function TogglePill({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={[
        "rounded-full px-3 py-1 text-sm border transition",
        active ? "bg-primary text-primary-foreground border-primary" : "hover:bg-muted",
      ].join(" ")}
    >
      {children}
    </button>
  );
}

function clampLevel(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(9, Math.floor(value)));
}

function toggleSelection(values: string[], setValues: (next: string[]) => void, value: string) {
  setValues(values.includes(value) ? values.filter((v) => v !== value) : [...values, value]);
}

function ToggleGroup({ label, options, selected, setSelected, allTitle }: ToggleGroupProps) {
  const allSelected = selected.length === 0 || selected.length === options.length;

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-sm font-medium min-w-[56px]">{label}</span>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setSelected([])}
        disabled={allSelected}
        title={allTitle}
      >
        All
      </Button>
      <div className="flex items-center gap-2 flex-wrap">
        {options.map((value) => (
          <TogglePill
            key={value}
            active={selected.includes(value)}
            onClick={() => toggleSelection(selected, setSelected, value)}
          >
            {value}
          </TogglePill>
        ))}
      </div>
    </div>
  );
}

export default function OrbsFilterBar({
  allTypes,
  allSets,
  allRarities,
  selectedTypes,
  setSelectedTypes,
  selectedSets,
  setSelectedSets,
  selectedRarities,
  setSelectedRarities,
  levelMin,
  levelMax,
  setLevelMin,
  setLevelMax,
  searchQuery,
  setSearchQuery,
  className = "",
}: Props) {
  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex items-end gap-2 flex-wrap">
        <div className="space-y-1">
          <label className="text-sm font-medium">Search</label>
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Type, set, rarity, awakened level"
            className="w-[220px]"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Level Min</label>
          <Input
            type="number"
            min={0}
            max={9}
            value={levelMin}
            onChange={(e) => {
              const parsed = Number(e.target.value);
              if (!Number.isFinite(parsed)) return;
              const nextMin = clampLevel(parsed);
              setLevelMin(nextMin);
              if (nextMin > levelMax) setLevelMax(nextMin);
            }}
            className="w-[90px]"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Level Max</label>
          <Input
            type="number"
            min={0}
            max={9}
            value={levelMax}
            onChange={(e) => {
              const parsed = Number(e.target.value);
              if (!Number.isFinite(parsed)) return;
              const nextMax = clampLevel(parsed);
              setLevelMax(nextMax);
              if (nextMax < levelMin) setLevelMin(nextMax);
            }}
            className="w-[90px]"
          />
        </div>
      </div>

      <ToggleGroup
        label="Types"
        options={allTypes}
        selected={selectedTypes}
        setSelected={setSelectedTypes}
        allTitle="Show all types"
      />

      <ToggleGroup
        label="Sets"
        options={allSets}
        selected={selectedSets}
        setSelected={setSelectedSets}
        allTitle="Show all sets"
      />

      <ToggleGroup
        label="Rarity"
        options={allRarities}
        selected={selectedRarities}
        setSelected={setSelectedRarities}
        allTitle="Show all rarities"
      />
    </div>
  );
}
