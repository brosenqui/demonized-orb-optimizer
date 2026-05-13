import type { OptimizeRawPayload, OrbIn, SharedSummary } from "./types";

export type ParsedProfile = {
  name: string;
  score: number | null;
  set_score: number | null;
  orb_score: number | null;
  is_partial: boolean;
  assignments: Record<string, OrbIn[]>;
};

export type ParsedResult = {
  combined_score: number | null;
  shared_summary: SharedSummary | null;
  run_diagnostics: Record<string, unknown> | null;
  profiles: ParsedProfile[];
};

export function parseResultsFromRaw(raw: OptimizeRawPayload | null | undefined): ParsedResult | null {
  if (!raw) return null;

  return {
    combined_score: raw.combined_score ?? null,
    shared_summary: raw.shared_summary ?? null,
    run_diagnostics: raw.run_diagnostics ?? null,
    profiles: raw.profiles.map((profile) => ({
      name: profile.name,
      score: profile.score ?? null,
      set_score: profile.set_score ?? null,
      orb_score: profile.orb_score ?? null,
      is_partial: profile.is_partial ?? false,
      assignments: profile.assignments ?? {},
    })),
  };
}
