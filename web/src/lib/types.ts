export type Rarity =
  | "Common"
  | "Magic"
  | "Rare"
  | "Epic"
  | "Legendary"
  | "Mythic";

export const rarityOptions: Rarity[] = [
  "Common",
  "Magic",
  "Rare",
  "Epic",
  "Legendary",
  "Mythic",
];

export const objectiveOptions: Array<"sets-first" | "types-first"> = [
  "sets-first",
  "types-first",
];

export type OrbIn = {
  type: string;
  set: string;
  rarity: string;
  value: number;
  level: number;
};

export type OptimizeProfileIn = {
  name: string;
  weight: number;
  objective: "sets-first" | "types-first";
  power: number;
  epsilon: number;
  set_priority: Record<string, number>;
  orb_weights: Record<string, number>;
  orb_level_weights: Record<string, number>;

  // NEW: per-profile category settings
  category_rarity?: Record<string, "Rare" | "Epic" | "Legendary" | "Mythic">;
  slots?: Record<string, number>; // optional direct slots override
};

export type OptimizeRequest = {
  orbs: OrbIn[];
  profiles: OptimizeProfileIn[];            // NOTE: no global slots anymore
  shareable_categories?: string[];          // stays global for now
  algorithm: "greedy";
  topk?: number;
  beam?: number;
  refine_passes?: number;
  refine_report?: boolean;
};

export type OptimizeResponse = {
  ok: boolean;
  result: {
    summary: any;
    raw: {
      combined_score?: number | null;
      profiles: Record<string, {
        set_score?: number;
        orb_score?: number;
        used_slots?: Record<string, number>; // NEW echo of slots used
        loadout: Record<string, Array<{
          type: string;
          set?: string;
          rarity: string;
          value: number;
          level: number;
          slot_index?: number;
        }>>;
      }>;
    };
    assign?: any;
  };
};
