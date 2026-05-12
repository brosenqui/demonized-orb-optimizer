import { useRef, useState, type ChangeEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import type { OrbIn } from "@/lib/types";
import { parseImportedOrbs } from "@/features/orbs/utils/orbInput";

type OrbImportDialogProps = {
  onImport: (orbs: OrbIn[]) => void;
};

export default function OrbImportDialog({ onImport }: OrbImportDialogProps) {
  const [open, setOpen] = useState(false);
  const [jsonText, setJsonText] = useState("");
  const [importError, setImportError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  async function handleFilePick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      setJsonText(text);
      setImportError(null);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to read file";
      setImportError(message);
    }
  }

  function resetImportForm() {
    if (fileRef.current) fileRef.current.value = "";
    setJsonText("");
    setImportError(null);
  }

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (!next) resetImportForm();
  }

  function handleImport() {
    setImportError(null);
    try {
      const normalized = parseImportedOrbs(jsonText);
      onImport(normalized);
      handleOpenChange(false);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Invalid JSON";
      setImportError(message);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline">Import JSON</Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Import Orbs (JSON)</DialogTitle>
          <DialogDescription>
            Paste JSON or upload a <code>.json</code> file. Importing replaces the current orb list.
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
            <Button variant="ghost" onClick={resetImportForm}>
              Clear File
            </Button>
          </div>

          <Textarea
            placeholder={`[\n  { "type": "Flame", "set": "Lucifer", "rarity": "Rare", "value": 0, "level": 1, "awakened": 2 },\n  { "type": "Steel", "set": "Mammon", "rarity": "Legendary", "value": 12.5, "level": 8, "awakened": 0 }\n]`}
            className="min-h-[180px]"
            value={jsonText}
            onChange={(event) => setJsonText(event.target.value)}
          />

          {importError && <p className="text-sm text-red-600">{importError}</p>}
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleImport}>Import</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
