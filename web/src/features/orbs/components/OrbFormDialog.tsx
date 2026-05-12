import type { Dispatch, SetStateAction } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select as UiSelect,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { rarityOptions, type OrbIn } from "@/lib/types";
import { ORB_SETS, ORB_TYPES } from "@/lib/orbData";
import { clamp } from "./OrbDisplay";

export type OrbFormState = {
  type: OrbIn["type"];
  set: OrbIn["set"];
  rarity: OrbIn["rarity"];
  value: number;
  level: number;
  awakened: number;
};

type OrbFormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isEditing: boolean;
  form: OrbFormState;
  setForm: Dispatch<SetStateAction<OrbFormState>>;
  onSave: () => void;
};

export default function OrbFormDialog({
  open,
  onOpenChange,
  isEditing,
  form,
  setForm,
  onSave,
}: OrbFormDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit Orb" : "Add Orb"}</DialogTitle>
          <DialogDescription>
            Set orb type, set, rarity, value, level, and awakened levels.
          </DialogDescription>
        </DialogHeader>

        <div className="grid sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-sm" htmlFor="orb-form-type">Type</label>
            <UiSelect
              value={form.type}
              onValueChange={(value) =>
                setForm((current) => ({ ...current, type: value as OrbIn["type"] }))
              }
            >
              <SelectTrigger className="w-full" id="orb-form-type">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                {ORB_TYPES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </UiSelect>
          </div>

          <div className="space-y-1">
            <label className="text-sm" htmlFor="orb-form-set">Set</label>
            <UiSelect
              value={form.set}
              onValueChange={(value) =>
                setForm((current) => ({ ...current, set: value as OrbIn["set"] }))
              }
            >
              <SelectTrigger className="w-full" id="orb-form-set">
                <SelectValue placeholder="Set" />
              </SelectTrigger>
              <SelectContent>
                {ORB_SETS.map((value) => (
                  <SelectItem key={value} value={value}>
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </UiSelect>
          </div>

          <div className="space-y-1">
            <label className="text-sm" htmlFor="orb-form-rarity">Rarity</label>
            <UiSelect
              value={form.rarity}
              onValueChange={(value) =>
                setForm((current) => ({ ...current, rarity: value as OrbIn["rarity"] }))
              }
            >
              <SelectTrigger className="w-full" id="orb-form-rarity">
                <SelectValue placeholder="Rarity" />
              </SelectTrigger>
              <SelectContent>
                {rarityOptions.map((value) => (
                  <SelectItem key={value} value={value}>
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </UiSelect>
          </div>

          <div className="space-y-1">
            <label className="text-sm" htmlFor="orb-form-value">Value</label>
            <Input
              id="orb-form-value"
              type="number"
              value={form.value}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  value: clamp(Number(event.target.value) || 0),
                }))
              }
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm" htmlFor="orb-form-level">Level</label>
            <Input
              id="orb-form-level"
              type="number"
              value={form.level}
              onChange={(event) => {
                const numeric = Number(event.target.value);
                setForm((current) => ({
                  ...current,
                  level: clamp(Number.isFinite(numeric) ? numeric : 0, 0, 9),
                }));
              }}
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm" htmlFor="orb-form-awakened">Awakened Levels</label>
            <Input
              id="orb-form-awakened"
              type="number"
              min={0}
              step={1}
              value={form.awakened}
              onChange={(event) => {
                const numeric = Number(event.target.value);
                setForm((current) => ({
                  ...current,
                  awakened: Math.max(0, Math.floor(Number.isFinite(numeric) ? numeric : 0)),
                }));
              }}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={onSave}>{isEditing ? "Save" : "Add"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
