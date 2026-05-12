// src/lib/applyTemplate.ts
import type { OptimizeProfileIn } from "./types";
import type { PriorityTemplate } from "./priorityTemplates";
import { PROFILE_DEFAULTS } from "./priorityTemplates";

function toNumberRecord(input?: Partial<Record<string, number>>): Record<string, number> | undefined {
  if (!input) return undefined;
  return Object.fromEntries(
    Object.entries(input).filter((entry): entry is [string, number] => Number.isFinite(entry[1]))
  );
}

/**
 * Destructive template application:
 * 1) Start from PROFILE_DEFAULTS (clears previous values/maps).
 * 2) Preserve the user's profile identity knobs: name + weight.
 * 3) Apply ONLY the fields present in the template.
 *    - If a map is omitted in the template, it stays empty (cleared).
 *    - If a primitive is omitted, it resets to the baseline default.
 */
export function applyTemplateToProfile(
  profile: OptimizeProfileIn,
  tpl: PriorityTemplate,
  base: OptimizeProfileIn = PROFILE_DEFAULTS
): OptimizeProfileIn {
  // 1) reset to baseline, 2) preserve friendly identity knobs
  const reset: OptimizeProfileIn = {
    ...base,
    name: profile.name,
    weight: profile.weight,
    power: profile.power,
    epsilon: profile.epsilon,
  };

  // 3) apply only what template specifies
  const next: OptimizeProfileIn = {
    ...reset,
    objective: tpl.objective ?? reset.objective,
    power: tpl.power ?? reset.power,
    epsilon: tpl.epsilon ?? reset.epsilon,
    categories: tpl.categories ? { ...tpl.categories } : reset.categories,
    set_priority: toNumberRecord(tpl.set_priority) ?? reset.set_priority,
    orb_weights: toNumberRecord(tpl.orb_weights) ?? reset.orb_weights,
    orb_level_weights: toNumberRecord(tpl.orb_level_weights) ?? reset.orb_level_weights,
  };

  return next;
}
