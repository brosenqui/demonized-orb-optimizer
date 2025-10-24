// src/lib/resultParser.ts
import type { OrbIn } from "./types";

/** Normalize one raw orb object to OrbIn. */
function toOrbIn(raw: any): OrbIn {
  const type = String(raw?.type ?? "").trim();
  const set = String(raw?.set ?? raw?.set_name ?? "").trim();
  const rarity = String(raw?.rarity ?? "Rare").trim();
  const value = Number.isFinite(Number(raw?.value)) ? Number(raw?.value) : 0;
  const level = Number.isFinite(Number(raw?.level)) ? Number(raw?.level) : 0;

  return {
    type: type || "Unknown",
    set: set || "Unknown",
    rarity: (rarity as OrbIn["rarity"]) || "Rare",
    value,
    level,
  };
}

type ParsedProfile = {
  name: string;
  score?: number | null;
  set_score?: number | null;
  orb_score?: number | null;
  assignments: Record<string, OrbIn[]>;
};

type ParsedResult = {
  combined_score: number | null;
  profiles: ParsedProfile[];
};

/**
 * Parses the API `result.raw` to a consistent, UI-friendly shape.
 * Supports the new **canonical** backend shape:
 *   raw.profiles: Array<{ name, set_score?, orb_score?, score?, assignments: {cat: Orb[]} }>
 *
 * Also remains defensive: it can still understand older shapes just in case.
 */
export function parseResultsFromRaw(raw: any): ParsedResult | null {
  if (!raw || typeof raw !== "object") return null;

  const combined_score =
    typeof raw.combined_score === "number" ? raw.combined_score : null;

  const profilesOut: ParsedProfile[] = [];

  // --- New canonical format: profiles is an ARRAY with `assignments` ---
  if (Array.isArray(raw.profiles)) {
    for (const p of raw.profiles) {
      const name = String(p?.name ?? "");
      const set_score =
        typeof p?.set_score === "number" ? p.set_score : null;
      const orb_score =
        typeof p?.orb_score === "number" ? p.orb_score : null;
      const score = typeof p?.score === "number" ? p.score : null;

      const assignments: Record<string, OrbIn[]> = {};
      const src = (p?.assignments && typeof p.assignments === "object") ? p.assignments : {};
      for (const [cat, arr] of Object.entries<any>(src)) {
        assignments[String(cat)] = Array.isArray(arr) ? arr.map(toOrbIn) : [];
      }

      profilesOut.push({ name, score, set_score, orb_score, assignments });
    }
    return { combined_score, profiles: profilesOut };
  }

  // --- (Fallback) Old shape A: raw.assign (object of profiles) ---
  if (raw.assign && typeof raw.assign === "object") {
    const scores = raw.profiles && typeof raw.profiles === "object" ? raw.profiles : {};
    for (const [name, catMap] of Object.entries<any>(raw.assign)) {
      const assignments: Record<string, OrbIn[]> = {};
      if (catMap && typeof catMap === "object") {
        for (const [cat, arr] of Object.entries<any>(catMap)) {
          assignments[String(cat)] = Array.isArray(arr) ? arr.map(toOrbIn) : [];
        }
      }
      const meta = (scores as any)[name] || {};
      profilesOut.push({
        name: String(name),
        score: typeof meta?.score === "number" ? meta.score : null,
        set_score: typeof meta?.set_score === "number" ? meta.set_score : null,
        orb_score: typeof meta?.orb_score === "number" ? meta.orb_score : null,
        assignments,
      });
    }
    return { combined_score, profiles: profilesOut };
  }

  // --- (Fallback) Old shape B: raw.profiles as OBJECT with `loadout` ---
  if (raw.profiles && typeof raw.profiles === "object") {
    for (const [name, meta] of Object.entries<any>(raw.profiles)) {
      const loadout = meta?.loadout && typeof meta.loadout === "object" ? meta.loadout : {};
      const assignments: Record<string, OrbIn[]> = {};
      for (const [cat, arr] of Object.entries<any>(loadout)) {
        assignments[String(cat)] = Array.isArray(arr) ? arr.map(toOrbIn) : [];
      }
      profilesOut.push({
        name: String(name),
        score: typeof meta?.score === "number" ? meta.score : null,
        set_score: typeof meta?.set_score === "number" ? meta.set_score : null,
        orb_score: typeof meta?.orb_score === "number" ? meta.orb_score : null,
        assignments,
      });
    }
    return { combined_score, profiles: profilesOut };
  }

  return null;
}
