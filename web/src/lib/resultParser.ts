import type { OptimizeRawPayload, OrbIn } from "./types";

export type ParsedProfile = {
  name: string;
  score: number | null;
  set_score: number | null;
  orb_score: number | null;
  assignments: Record<string, OrbIn[]>;
};

export type ParsedResult = {
  combined_score: number | null;
  profiles: ParsedProfile[];
};

export function parseResultsFromRaw(raw: OptimizeRawPayload | null | undefined): ParsedResult | null {
  if (!raw) return null;

  return {
    combined_score: raw.combined_score ?? null,
    profiles: raw.profiles.map((profile) => ({
      name: profile.name,
      score: profile.score ?? null,
      set_score: profile.set_score ?? null,
      orb_score: profile.orb_score ?? null,
      assignments: profile.assignments ?? {},
    })),
  };
}
