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
  used_slots: Record<string, number>;
  assignments: Record<string, OrbIn[]>;
};

export type OptimizeRawPayload = {
  combined_score: number | null;
  profiles: OptimizeRawProfile[];
};

export type OptimizeSummaryProfile = {
  name: string;
  score: number | null;
  set_score: number | null;
  orb_score: number | null;
};

export type OptimizeSummary = {
  combined_score: number | null;
  per_profile: OptimizeSummaryProfile[];
};

export type OptimizeResult = {
  summary: OptimizeSummary;
  raw: OptimizeRawPayload;
};

export type OptimizeResponse = {
  ok: true;
  result: OptimizeResult;
};
