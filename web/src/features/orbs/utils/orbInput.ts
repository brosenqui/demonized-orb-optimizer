import { orbRarityOptions, type OrbIn, type OrbRarity } from "@/lib/types";

export function clampNonNegativeInt(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.floor(value));
}

export function clampRange(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  return Math.max(min, Math.min(max, value));
}

export function sanitizeOrbInput(input: OrbIn): OrbIn {
  const type = input.type.trim();
  const set = input.set.trim();
  return {
    ...input,
    type: type.length > 0 ? type : "Unknown",
    set: set.length > 0 ? set : "Unknown",
    rarity: normalizeOrbRarity(input.rarity),
    value: Number.isFinite(input.value) ? Math.max(0, input.value) : 0,
    level: clampRange(Math.floor(input.level), 0, 9),
    awakened: clampNonNegativeInt(input.awakened),
  };
}

function normalizeOrbRarity(value: string): OrbRarity {
  const normalized = orbRarityOptions.find((rarity) => rarity === value);
  return normalized ?? "Rare";
}

export function normalizeOrb(input: unknown): OrbIn | null {
  if (typeof input !== "object" || input === null) return null;

  const raw = input as Record<string, unknown>;
  const type = String(raw.type ?? "").trim();
  const set = String(raw.set ?? raw.set_name ?? "").trim();

  if (!type || !set) return null;

  return sanitizeOrbInput({
    type,
    set,
    rarity: normalizeOrbRarity(String(raw.rarity ?? "Rare")),
    value: Number(raw.value ?? 0),
    level: Number(raw.level ?? 0),
    awakened: Number(raw.awakened ?? 0),
    slot_index:
      typeof raw.slot_index === "number" && Number.isInteger(raw.slot_index)
        ? raw.slot_index
        : undefined,
  });
}

export function parseImportedOrbs(text: string): OrbIn[] {
  const parsed: unknown = JSON.parse(text);
  const items =
    Array.isArray(parsed)
      ? parsed
      : parsed && typeof parsed === "object" && Array.isArray((parsed as { orbs?: unknown[] }).orbs)
        ? (parsed as { orbs: unknown[] }).orbs
        : null;

  if (!Array.isArray(items)) {
    throw new Error("JSON must be an array of orbs or an object with { orbs: [...] }");
  }

  const normalized = items
    .map((item) => normalizeOrb(item))
    .filter((orb): orb is OrbIn => orb !== null)
    .map(sanitizeOrbInput);

  if (normalized.length === 0) {
    throw new Error("No valid orbs found in the JSON.");
  }

  return normalized;
}
