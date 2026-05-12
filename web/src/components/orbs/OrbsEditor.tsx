import React, { useRef, useState } from "react";
import Section from "../ui/Section";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "../ui/dialog";
import {
  Select as UiSelect,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "../ui/select";
import { ChevronDown, ChevronUp, Filter, RotateCcw } from "lucide-react";

import OrbGrid from "./OrbGrid";
import OrbsFilterBar from "./OrbsFilterBar";
import OrbFormDialog, { type OrbFormState } from "./OrbFormDialog";
import { useOrbFilters } from "./useOrbFilters";
import { rarityOptions, type OrbIn } from "../../lib/types";
import { ORB_TYPES, ORB_SETS } from "../../lib/orbData";
import { Density, normalizeOrb, clamp } from "./OrbDisplay";

export default function OrbsEditor({
  orbs,
  setOrbs,
}: {
  orbs: OrbIn[];
  setOrbs: (o: OrbIn[]) => void;
}) {
  // Density selector
  const [density, setDensity] = useState<Density>("cozy");

  // Import dialog
  const [openImport, setOpenImport] = useState(false);
  const [jsonText, setJsonText] = useState("");
  const [importError, setImportError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  // Add/Edit dialog
  const [openForm, setOpenForm] = useState(false);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [form, setForm] = useState<OrbFormState>(() => ({
    type: ORB_TYPES[0],
    set: ORB_SETS[0],
    rarity: "Rare",
    value: 0,
    level: 0,
    awakened: 0,
  }));
  const [filtersOpen, setFiltersOpen] = useState(true);
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

  // ---- Import handlers ----
  async function handleFilePick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      setJsonText(text);
      setImportError(null);
    } catch (err: any) {
      setImportError(err?.message || "Failed to read file");
    }
  }

  function parseAndReplaceFromText() {
    setImportError(null);
    try {
      const data = JSON.parse(jsonText);
      let arr: any[] = [];

      if (Array.isArray(data)) arr = data;
      else if (data && Array.isArray(data.orbs)) arr = data.orbs;
      else throw new Error("JSON must be an array of orbs or an object with { orbs: [...] }");

      const normalized: OrbIn[] = [];
      for (const item of arr) {
        const o = normalizeOrb(item);
        if (o) normalized.push(o);
      }
      if (normalized.length === 0) throw new Error("No valid orbs found in the JSON.");

      setOrbs(normalized); // replace list
      setOpenImport(false);
      setJsonText("");
      // keep current filters; they still apply to the new list
    } catch (e: any) {
      setImportError(e?.message || "Invalid JSON");
    }
  }

  // ---- Add/Edit handlers ----
  function openAdd() {
    setEditingIndex(null);
    setForm({
      type: ORB_TYPES[0],
      set: ORB_SETS[0],
      rarity: "Rare",
      value: 0,
      level: 0,
      awakened: 0,
    });
    setOpenForm(true);
  }

  function openEdit(index: number) {
    const o = orbs[index];
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
  }

  function saveForm() {
    const cleaned: OrbIn = {
      type: form.type,
      set: form.set,
      rarity: form.rarity,
      value: clamp(Number(form.value) || 0),
      level: clamp(Number(form.level) || 0, 0, 9),
      awakened: Math.max(0, Math.floor(Number(form.awakened) || 0)),
    };
    if (editingIndex === null) {
      setOrbs([...orbs, cleaned]);
    } else {
      const next = [...orbs];
      next[editingIndex] = cleaned;
      setOrbs(next);
    }
    setOpenForm(false);
  }

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

          {/* Import JSON dialog */}
          <Dialog open={openImport} onOpenChange={setOpenImport}>
            <DialogTrigger asChild>
              <Button variant="outline">Import JSON</Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Import Orbs (JSON)</DialogTitle>
                <DialogDescription>
                  Paste JSON or upload a <code>.json</code> file. Importing will <strong>replace</strong> the current orb list.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Input
                    ref={fileRef}
                    type="file"
                    accept="application/json,.json"
                    onChange={handleFilePick}
                  />
                  <Button
                    variant="ghost"
                    onClick={() => {
                      if (fileRef.current) fileRef.current.value = "";
                      setJsonText("");
                      setImportError(null);
                    }}
                  >
                    Clear File
                  </Button>
                </div>

                <Textarea
                  placeholder={`[\n  { "type": "Flame", "set": "Lucifer", "rarity": "Rare", "value": 0, "level": 1, "awakened": 2 },\n  { "type": "Steel", "set": "Mammon", "rarity": "Legendary", "value": 12.5, "level": 8, "awakened": 0 }\n]`}
                  className="min-h-[180px]"
                  value={jsonText}
                  onChange={(e) => setJsonText(e.target.value)}
                />

                {importError && <p className="text-sm text-red-600">{importError}</p>}
              </div>

              <DialogFooter>
                <Button variant="secondary" onClick={() => setOpenImport(false)}>
                  Cancel
                </Button>
                <Button onClick={parseAndReplaceFromText}>Import</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          <Button onClick={openAdd}>Add Orb</Button>
          <Button variant="destructive" onClick={() => setOrbs([])}>
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
              <Button variant="ghost" size="sm" onClick={resetFilters}>
                <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                Reset
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setFiltersOpen((open) => !open)}
              aria-expanded={filtersOpen}
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
          onTileClick={(i) => {
            const originalIndex = visibleOrbIndices[i];
            if (originalIndex !== undefined) openEdit(originalIndex);
          }}
          onTileDelete={(i) => {
            const originalIndex = visibleOrbIndices[i];
            if (originalIndex !== undefined) {
              setOrbs(orbs.filter((_, idx) => idx !== originalIndex));
            }
          }}
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
