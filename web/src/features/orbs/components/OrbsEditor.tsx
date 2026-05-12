import { useCallback, useEffect, useRef, useState } from "react";
import Section from "@/components/ui/Section";
import { Button } from "@/components/ui/button";
import {
  Select as UiSelect,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { ChevronDown, ChevronUp, Filter, RotateCcw } from "lucide-react";

import OrbGrid from "./OrbGrid";
import OrbImportDialog from "./OrbImportDialog";
import OrbsFilterBar from "./OrbsFilterBar";
import OrbFormDialog, { type OrbFormState } from "./OrbFormDialog";
import { useOrbFilters } from "@/features/orbs/hooks/useOrbFilters";
import { sanitizeOrbInput } from "@/features/orbs/utils/orbInput";
import { rarityOptions, type OrbIn } from "@/lib/types";
import { ORB_TYPES, ORB_SETS } from "@/lib/orbData";
import type { Density } from "./OrbDisplay";

function createDefaultOrbFormState(): OrbFormState {
  return {
    type: ORB_TYPES[0],
    set: ORB_SETS[0],
    rarity: "Rare",
    value: 0,
    level: 0,
    awakened: 0,
  };
}

function isTextEntryTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    target.isContentEditable
  );
}

export default function OrbsEditor({
  orbs,
  setOrbs,
}: {
  orbs: OrbIn[];
  setOrbs: (o: OrbIn[]) => void;
}) {
  // Density selector
  const [density, setDensity] = useState<Density>("cozy");

  // Add/Edit dialog
  const [openForm, setOpenForm] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [form, setForm] = useState<OrbFormState>(() => createDefaultOrbFormState());
  const [filtersOpen, setFiltersOpen] = useState(true);
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const {
    selectedTypes,
    setSelectedTypes,
    selectedSets,
    setSelectedSets,
    selectedRarities,
    setSelectedRarities,
    levelMin,
    setLevelMin,
    levelMax,
    setLevelMax,
    searchQuery,
    setSearchQuery,
    visibleOrbIndices,
    visibleOrbs,
    hasActiveFilters,
    activeFilterGroups,
    resetFilters,
  } = useOrbFilters(orbs);
  const visibleCount = visibleOrbs.length;
  const totalCount = orbs.length;

  // ---- Add/Edit handlers ----
  const openAdd = useCallback(() => {
    setEditingIndex(null);
    setForm(createDefaultOrbFormState());
    setOpenForm(true);
  }, []);

  const openEdit = useCallback((index: number) => {
    const o = orbs[index];
    if (!o) return;

    setEditingIndex(index);
    setForm({
      type: o.type,
      set: o.set,
      rarity: o.rarity,
      value: o.value,
      level: o.level,
      awakened: Math.max(0, Math.floor(Number(o.awakened) || 0)),
    });
    setOpenForm(true);
  }, [orbs]);

  const saveForm = useCallback(() => {
    const cleaned: OrbIn = sanitizeOrbInput({
      type: form.type,
      set: form.set,
      rarity: form.rarity,
      value: Number(form.value) || 0,
      level: Number(form.level) || 0,
      awakened: Math.max(0, Math.floor(Number(form.awakened) || 0)),
    });

    if (editingIndex === null) {
      setOrbs([...orbs, cleaned]);
    } else {
      const next = [...orbs];
      next[editingIndex] = cleaned;
      setOrbs(next);
    }

    setOpenForm(false);
    setEditingIndex(null);
  }, [editingIndex, form, orbs, setOrbs]);

  const handleDeleteAtVisibleIndex = useCallback((visibleIndex: number) => {
    const originalIndex = visibleOrbIndices[visibleIndex];
    if (originalIndex === undefined) return;
    setOrbs(orbs.filter((_, index) => index !== originalIndex));
  }, [orbs, setOrbs, visibleOrbIndices]);

  const handleEditAtVisibleIndex = useCallback((visibleIndex: number) => {
    const originalIndex = visibleOrbIndices[visibleIndex];
    if (originalIndex === undefined) return;
    openEdit(originalIndex);
  }, [openEdit, visibleOrbIndices]);

  const clearOrbs = useCallback(() => {
    if (orbs.length === 0) return;
    const confirmed = window.confirm("Clear all orbs from the current collection?");
    if (!confirmed) return;
    setOrbs([]);
  }, [orbs.length, setOrbs]);

  useEffect(() => {
    function handleGlobalShortcuts(event: KeyboardEvent) {
      if (event.defaultPrevented) return;

      if (event.altKey && !event.shiftKey && !event.metaKey && !event.ctrlKey) {
        if (event.key.toLowerCase() === "a") {
          event.preventDefault();
          openAdd();
          return;
        }

        if (event.key.toLowerCase() === "f") {
          event.preventDefault();
          setFiltersOpen((open) => !open);
          return;
        }
      }

      if (
        event.key === "/" &&
        !event.altKey &&
        !event.ctrlKey &&
        !event.metaKey &&
        !isTextEntryTarget(event.target)
      ) {
        event.preventDefault();
        setFiltersOpen(true);
        searchInputRef.current?.focus();
      }
    }

    window.addEventListener("keydown", handleGlobalShortcuts);
    return () => window.removeEventListener("keydown", handleGlobalShortcuts);
  }, [openAdd]);

  return (
    <Section
      title="Orbs"
      helpText="Enter and manage your collection of orbs here. You can add orbs manually, import JSON, set awakened levels, adjust display density, and filter/sort with search, type, set, rarity, and level."
      actions={
        <div className="flex gap-2 items-center">
          {/* Density selector */}
          <UiSelect value={density} onValueChange={(v) => setDensity(v as Density)}>
            <SelectTrigger className="w-[170px]">
              <SelectValue placeholder="Density" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="comfortable">Comfortable (6/row)</SelectItem>
              <SelectItem value="cozy">Cozy (9/row)</SelectItem>
              <SelectItem value="compact">Compact (12/row)</SelectItem>
            </SelectContent>
          </UiSelect>

          <OrbImportDialog onImport={setOrbs} />

          <Button onClick={openAdd} title="Shortcut: Alt+A">
            Add Orb
          </Button>
          <Button
            variant="destructive"
            onClick={clearOrbs}
            title="Shortcut: confirm clear"
            aria-label="Clear all orbs"
          >
            Clear
          </Button>
        </div>
      }
    >
      {/* Filters */}
      <div className="mb-4 rounded-md border border-border p-3">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-medium inline-flex items-center gap-2">
            <Filter className="h-4 w-4" aria-hidden="true" />
            Filters
          </p>
          <div className="flex items-center gap-2">
            {totalCount > 0 && (
              <span className="text-xs text-muted-foreground">
                {visibleCount}/{totalCount} shown
              </span>
            )}
            {hasActiveFilters && (
              <span className="text-xs text-muted-foreground">
                {activeFilterGroups} active
              </span>
            )}
            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={resetFilters} aria-label="Reset all filters">
                <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                Reset
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setFiltersOpen((open) => !open)}
              aria-expanded={filtersOpen}
              aria-label={filtersOpen ? "Collapse filters" : "Expand filters"}
              title={filtersOpen ? "Collapse filters" : "Expand filters"}
              className="h-7 w-7 p-0"
            >
              {filtersOpen ? (
                <ChevronUp className="h-4 w-4" aria-hidden="true" />
              ) : (
                <ChevronDown className="h-4 w-4" aria-hidden="true" />
              )}
            </Button>
          </div>
        </div>

        {filtersOpen && (
          <div className="mt-3">
            <OrbsFilterBar
              allTypes={ORB_TYPES}
              allSets={ORB_SETS}
              allRarities={rarityOptions}
              selectedTypes={selectedTypes}
              setSelectedTypes={setSelectedTypes}
              selectedSets={selectedSets}
              setSelectedSets={setSelectedSets}
              selectedRarities={selectedRarities}
              setSelectedRarities={setSelectedRarities}
              levelMin={levelMin}
              levelMax={levelMax}
              setLevelMin={setLevelMin}
              setLevelMax={setLevelMax}
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              searchInputRef={searchInputRef}
            />
          </div>
        )}
      </div>

      {/* Grid + empty states */}
      {orbs.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No orbs yet. Import JSON or click “Add Orb”.
        </p>
      ) : visibleOrbs.length === 0 ? (
        <div className="text-sm text-muted-foreground">
          No orbs match your filters.
          {hasActiveFilters && (
            <>
              {" "}
              <button
                type="button"
                className="underline underline-offset-4"
                onClick={resetFilters}
              >
                Reset filters
              </button>
              .
            </>
          )}
        </div>
      ) : (
        <OrbGrid
          orbs={visibleOrbs}
          density={density}
          onTileClick={handleEditAtVisibleIndex}
          onTileDelete={handleDeleteAtVisibleIndex}
        />
      )}

      <OrbFormDialog
        open={openForm}
        onOpenChange={setOpenForm}
        isEditing={editingIndex !== null}
        form={form}
        setForm={setForm}
        onSave={saveForm}
      />
    </Section>
  );
}
