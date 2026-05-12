import type { OptimizeRawPayload, OrbIn, SharedSummary } from "./types";

export type ParsedProfile = {
  name: string;
  score: number | null;
  set_score: number | null;
  orb_score: number | null;
  requested_slots: number;
  filled_slots: number;
  is_partial: boolean;
  assignments: Record<string, OrbIn[]>;
};

export type ParsedResult = {
  combined_score: number | null;
  requested_slots: number;
  filled_slots: number;
  is_partial: boolean;
  shared_summary: SharedSummary | null;
  profiles: ParsedProfile[];
};

export function parseResultsFromRaw(raw: OptimizeRawPayload | null | undefined): ParsedResult | null {
  if (!raw) return null;

  return {
    combined_score: raw.combined_score ?? null,
    requested_slots: raw.requested_slots ?? 0,
    filled_slots: raw.filled_slots ?? 0,
    is_partial: raw.is_partial ?? false,
    shared_summary: raw.shared_summary ?? null,
    profiles: raw.profiles.map((profile) => ({
      name: profile.name,
      score: profile.score ?? null,
      set_score: profile.set_score ?? null,
      orb_score: profile.orb_score ?? null,
      requested_slots: profile.requested_slots ?? 0,
      filled_slots: profile.filled_slots ?? 0,
      is_partial: profile.is_partial ?? false,
      assignments: profile.assignments ?? {},
    })),
  };
}
