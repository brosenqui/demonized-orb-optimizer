export const orbRarityOptions = [
  "Common",
  "Magic",
  "Rare",
  "Epic",
  "Legendary",
  "Mythic",
] as const;

export type OrbRarity = (typeof orbRarityOptions)[number];

export const categoryRarityOptions = ["Rare", "Epic", "Legendary", "Mythic"] as const;

export type CategoryRarity = (typeof categoryRarityOptions)[number];

export const rarityOptions = orbRarityOptions;

export const objectiveOptions = ["sets-first", "types-first"] as const;

export type Objective = (typeof objectiveOptions)[number];

export type OrbIn = {
  type: string;
  set: string;
  rarity: OrbRarity;
  value: number;
  level: number;
  awakened: number;
  slot_index?: number;
};

export type OptimizeProfileIn = {
  name: string;
  weight: number;
  objective: Objective;
  power: number;
  epsilon: number;
  set_priority: Record<string, number>;
  orb_weights: Record<string, number>;
  orb_level_weights: Record<string, number>;
  categories?: Record<string, CategoryRarity>;
  slots?: Record<string, number>;
};

export type OptimizeRequest = {
  orbs: OrbIn[];
  profiles: OptimizeProfileIn[];
  shareable_categories?: string[];
  algorithm: "greedy";
};

export type OptimizeRawProfile = {
  name: string;
  score: number | null;
  set_score: number | null;
  orb_score: number | null;
  requested_slots: number;
  filled_slots: number;
  is_partial: boolean;
  assignments: Record<string, OrbIn[]>;
};

export type SharedSlotProfileImpact = {
  profile: string;
  selected_score: number;
  solo_best_score: number;
  compromise_loss: number;
  selected_d_set: number;
  selected_d_orb: number;
  solo_best_d_set: number;
  solo_best_d_orb: number;
  cap_limited: boolean;
};

export type SharedSlotAssignment = {
  category: string;
  slot_index: number;
  profiles: string[];
  is_uniform: boolean;
  orb: OrbIn | null;
  profile_orbs: Record<string, OrbIn | null>;
  profile_impacts: SharedSlotProfileImpact[];
};

export type SharedSummary = {
  requested_slots: number;
  filled_slots: number;
  is_partial: boolean;
  requested_positions: number;
  filled_positions: number;
  active_sets: Record<string, number>;
  totals_by_type: Record<string, number>;
  compromise_loss_total: number;
  compromise_loss_by_profile: Record<string, number>;
  cap_limited_slots_by_profile: Record<string, number>;
  slots: SharedSlotAssignment[];
};

export type OptimizeRawPayload = {
  combined_score: number | null;
  requested_slots: number;
  filled_slots: number;
  is_partial: boolean;
  shared_summary: SharedSummary | null;
  run_diagnostics: Record<string, unknown> | null;
  profiles: OptimizeRawProfile[];
};

export type OptimizeSummaryProfile = {
  name: string;
  score: number | null;
  set_score: number | null;
  orb_score: number | null;
  requested_slots: number;
  filled_slots: number;
  is_partial: boolean;
};

export type OptimizeSummary = {
  combined_score: number | null;
  requested_slots: number;
  filled_slots: number;
  is_partial: boolean;
  shared_summary: SharedSummary | null;
  run_diagnostics: Record<string, unknown> | null;
  profiles: OptimizeSummaryProfile[];
};

export type OptimizeResult = {
  summary: OptimizeSummary;
  raw: OptimizeRawPayload;
};

export type OptimizeResponse = {
  ok: true;
  result: OptimizeResult;
};
