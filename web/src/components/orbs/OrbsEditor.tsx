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

import OrbGrid from "./OrbGrid";
import type { OrbIn } from "../../lib/types";
import { ORB_TYPES, ORB_SETS } from "../../lib/orbData";
import { Density, normalizeOrb, clamp } from "./orbDisplay";

// --- Add/Edit form state type ---
type OrbFormState = {
  type: OrbIn["type"];
  set: OrbIn["set"];
  rarity: OrbIn["rarity"];
  value: number;
  level: number;
};

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
  }));

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

  function removeOrb(index: number) {
    setOrbs(orbs.filter((_, i) => i !== index));
  }

  return (
    <Section
      title="Orbs"
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
                  placeholder={`[\n  { "type": "Flame", "set": "Lucifer", "rarity": "Rare", "value": 0, "level": 1 },\n  { "type": "Steel", "set": "Mammon", "rarity": "Legendary", "value": 12.5, "level": 8 }\n]`}
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
      {orbs.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No orbs yet. Import JSON or click “Add Orb”.
        </p>
      ) : (
        <OrbGrid
          orbs={orbs}
          density={density}
          onTileClick={openEdit}
          onTileDelete={removeOrb}
        />
      )}

      {/* Add/Edit Orb Dialog */}
      <Dialog open={openForm} onOpenChange={setOpenForm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingIndex === null ? "Add Orb" : "Edit Orb"}</DialogTitle>
          </DialogHeader>

          <div className="grid sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-sm">Type</label>
              <UiSelect
                value={form.type}
                onValueChange={(val) => setForm((f) => ({ ...f, type: val as OrbIn["type"] }))}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  {ORB_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </UiSelect>
            </div>

            <div className="space-y-1">
              <label className="text-sm">Set</label>
              <UiSelect
                value={form.set}
                onValueChange={(val) => setForm((f) => ({ ...f, set: val as OrbIn["set"] }))}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Set" />
                </SelectTrigger>
                <SelectContent>
                  {ORB_SETS.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </UiSelect>
            </div>

            <div className="space-y-1">
              <label className="text-sm">Rarity</label>
              <UiSelect
                value={form.rarity}
                onValueChange={(val) => setForm((f) => ({ ...f, rarity: val as OrbIn["rarity"] }))}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Rarity" />
                </SelectTrigger>
                <SelectContent>
                  {["Common","Magic","Rare","Epic","Legendary","Mythic"].map((r) => (
                    <SelectItem key={r} value={r}>
                      {r}
                    </SelectItem>
                  ))}
                </SelectContent>
              </UiSelect>
            </div>

            <div className="space-y-1">
              <label className="text-sm">Value</label>
              <Input
                type="number"
                value={form.value}
                onChange={(e) =>
                  setForm((f) => ({ ...f, value: clamp(Number(e.target.value) || 0) }))
                }
              />
            </div>

            <div className="space-y-1">
              <label className="text-sm">Level</label>
              <Input
                type="number"
                value={form.level}
                onChange={(e) => {
                  const n = Number(e.target.value);
                  setForm((f) => ({ ...f, level: clamp(Number.isFinite(n) ? n : 0, 0, 9) }));
                }}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="secondary" onClick={() => setOpenForm(false)}>
              Cancel
            </Button>
            <Button onClick={saveForm}>{editingIndex === null ? "Add" : "Save"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Section>
  );
}
