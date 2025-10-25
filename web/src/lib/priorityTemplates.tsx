// src/lib/priorityTemplates.ts
import { OrbType, OrbSet } from "./orbData";
import type { OptimizeProfileIn } from "./types";

/**
 * Baseline defaults used when (re)applying templates.
 * We intentionally keep these "empty" so a destructive apply clears old keys.
 * Name/weight are preserved from the existing profile (not taken from here).
 */
export const PROFILE_DEFAULTS: OptimizeProfileIn = {
  name: "New Profile",
  weight: 1,
  objective: "sets-first",
  power: 2.0,
  epsilon: 0.02,
  categories: {},
  set_priority: {},
  orb_weights: {},
  orb_level_weights: {},
};

export type PriorityTemplate = {
  id: string;
  label: string;
  description?: string;

  // Core knobs your profiles already have
  objective?: string;
  power?: number;
  epsilon?: number;

  categories?: Record<string, string>;

  // Optional weight maps (only applied if you use them in OptimizeProfileIn)
  set_priority?: Record<OrbSet, number>;
  orb_weights?: Record<OrbType, number>;
  orb_level_weights?: Record<OrbType, number>;
};

export const PRIORITY_TEMPLATES: PriorityTemplate[] = [
  {
    id: "Early Game - Stages",
    label: "Early Game - Stages",
    description: "Best suited for early game players focusing on stage progression.",
    objective: "sets-first",
    power: 2.0,
    epsilon: 0.02,
    set_priority: {
        Beelzebub: 5,
        Mammon: 4
    },
    orb_weights: {
        Flame: 2,
        Lightning: 2,
        Sun: 2
    }
  },
  {
    id: "Mid Game - Stages",
    label: "Mid Game - Stages",
    description: "Ideal for mid game players aiming to balance stage progression and versatility.",
    objective: "sets-first",
    power: 2.5,
    epsilon: 0.02,
    set_priority: {
        Leviathan: 5,
        Beelzebub: 3,
        Belphegor: 3
    },
    orb_weights: { 
        Steel: 3,
        Wind: 2,
        Sun: 2,
        Lightning: 2
     },
     orb_level_weights: {
        Wind: 3,
        Steel: 3
     }
  },
  {
    id: "Late Game - Stages",
    label: "Late Game - Stages",
    description: "Ideal for late game players focusing on maximizing stage progression with high-level orbs.",
    objective: "sets-first",
    power: 2.5,
    epsilon: 0.02,
    set_priority: {
        Leviathan: 5,
        Belphegor: 3
    },
    orb_weights: { 
        Steel: 5,
        Wind: 3,
        Earth: 3
     },
     orb_level_weights: {
        Earth: 5,
        Wind: 3,
        Steel: 3
     }
  },
];
