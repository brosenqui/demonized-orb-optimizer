import { CATEGORIES } from "@/lib/categoryData";
import {
  cumulativeLevelGateBonus,
  ORB_LEVEL_GATE_STAT_BY_TYPE,
} from "@/lib/orbLevelGateData";
import { setBonusTotalsFromCounts } from "@/lib/setBonusData";
import type { OrbIn, SharedSummary } from "@/lib/types";

export type Assignments = Record<string, OrbIn[]>;
export type SharedProfileStats = {
  shared_slot_count: number;
  specific_slot_count: number;
  shared_total_value: number;
  specific_total_value: number;
  shared_active_sets: Array<[string, number]>;
  shared_totals_by_type: Array<[string, number]>;
  specific_active_sets: Array<[string, number]>;
  specific_totals_by_type: Array<[string, number]>;
  shared_set_bonus_stats: Array<[string, number]>;
  specific_set_bonus_stats: Array<[string, number]>;
  shared_level_gate_stats: Array<[string, number]>;
  specific_level_gate_stats: Array<[string, number]>;
  shared_with: Array<[string, number]>;
  compromise_loss: number;
  cap_limited_slots: number;
};

function orderedNumericEntries(values: Map<string, number>): Array<[string, number]> {
  return [...values.entries()].sort(
    (left, right) => right[1] - left[1] || left[0].localeCompare(right[0])
  );
}

export function orderedCategories(assignments: Assignments): string[] {
  const order = [...CATEGORIES];
  return Object.keys(assignments).sort((left, right) => {
    const leftIndex = order.indexOf(left as (typeof CATEGORIES)[number]);
    const rightIndex = order.indexOf(right as (typeof CATEGORIES)[number]);
    const normalizedLeft = leftIndex === -1 ? Number.MAX_SAFE_INTEGER : leftIndex;
    const normalizedRight = rightIndex === -1 ? Number.MAX_SAFE_INTEGER : rightIndex;
    return normalizedLeft - normalizedRight || left.localeCompare(right, undefined, { numeric: true });
  });
}

export function flattenAssignments(assignments: Assignments): OrbIn[] {
  return Object.values(assignments).flat();
}

export function activeSetCounts(orbs: readonly OrbIn[]): Array<[string, number]> {
  const counts = new Map<string, number>();
  for (const orb of orbs) {
    const key = orb.set || "Unknown";
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return [...counts.entries()].sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]));
}

export function totalsByType(orbs: readonly OrbIn[]): Array<[string, number]> {
  const totals = new Map<string, number>();
  for (const orb of orbs) {
    const key = orb.type || "Unknown";
    const value = Number.isFinite(orb.value) ? orb.value : 0;
    totals.set(key, (totals.get(key) ?? 0) + value);
  }
  return [...totals.entries()].sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]));
}

export function levelGateStatTotals(orbs: readonly OrbIn[]): Array<[string, number]> {
  const totals = new Map<string, number>();
  for (const orb of orbs) {
    const statName = ORB_LEVEL_GATE_STAT_BY_TYPE[orb.type];
    if (!statName) continue;
    const bonus = cumulativeLevelGateBonus(orb.type, orb.level);
    if (!Number.isFinite(bonus) || bonus <= 0) continue;
    totals.set(statName, (totals.get(statName) ?? 0) + bonus);
  }
  return [...totals.entries()].sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]));
}

function setCounts(orbs: readonly OrbIn[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const orb of orbs) {
    const setName = orb.set || "Unknown";
    counts.set(setName, (counts.get(setName) ?? 0) + 1);
  }
  return counts;
}

function toSortedEntries(values: Map<string, number>): Array<[string, number]> {
  return [...values.entries()].sort(
    (left, right) => right[1] - left[1] || left[0].localeCompare(right[0])
  );
}

function subtractMaps(total: Map<string, number>, baseline: Map<string, number>): Map<string, number> {
  const keys = new Set<string>([...total.keys(), ...baseline.keys()]);
  const next = new Map<string, number>();
  for (const key of keys) {
    const value = (total.get(key) ?? 0) - (baseline.get(key) ?? 0);
    if (Math.abs(value) < 1e-9) continue;
    next.set(key, value);
  }
  return next;
}

export function sharedStatsForProfile(
  assignments: Assignments,
  sharedSummary: SharedSummary | null | undefined,
  profileName: string
): SharedProfileStats {
  const sharedSlotKeys = new Set<string>();
  const sharedOrbs: OrbIn[] = [];
  const specificOrbs: OrbIn[] = [];

  const sharedWithCounts = new Map<string, number>();
  let compromiseLoss = 0;
  let capLimitedSlots = 0;

  for (const slot of sharedSummary?.slots ?? []) {
    if (!slot.profiles.includes(profileName)) continue;
    sharedSlotKeys.add(`${slot.category}::${slot.slot_index}`);

    for (const otherProfile of slot.profiles) {
      if (otherProfile === profileName) continue;
      sharedWithCounts.set(
        otherProfile,
        (sharedWithCounts.get(otherProfile) ?? 0) + 1
      );
    }

    const impact = slot.profile_impacts.find((candidate) => candidate.profile === profileName);
    if (impact) {
      compromiseLoss += Number.isFinite(impact.compromise_loss) ? impact.compromise_loss : 0;
      if (impact.cap_limited) capLimitedSlots += 1;
    }
  }

  for (const [category, orbs] of Object.entries(assignments)) {
    for (const [index, orb] of orbs.entries()) {
      const slotIndex = Math.max(0, orb.slot_index ?? index);
      if (sharedSlotKeys.has(`${category}::${slotIndex}`)) {
        sharedOrbs.push(orb);
      } else {
        specificOrbs.push(orb);
      }
    }
  }

  const sharedTotalValue = sharedOrbs.reduce(
    (sum, orb) => sum + (Number.isFinite(orb.value) ? orb.value : 0),
    0
  );
  const specificTotalValue = specificOrbs.reduce(
    (sum, orb) => sum + (Number.isFinite(orb.value) ? orb.value : 0),
    0
  );

  const sharedSetCounts = setCounts(sharedOrbs);
  const totalSetCounts = setCounts([...sharedOrbs, ...specificOrbs]);
  const sharedSetBonusTotals = setBonusTotalsFromCounts(sharedSetCounts);
  const totalSetBonusTotals = setBonusTotalsFromCounts(totalSetCounts);
  const specificSetBonusTotals = subtractMaps(totalSetBonusTotals, sharedSetBonusTotals);

  return {
    shared_slot_count: sharedOrbs.length,
    specific_slot_count: specificOrbs.length,
    shared_total_value: sharedTotalValue,
    specific_total_value: specificTotalValue,
    shared_active_sets: activeSetCounts(sharedOrbs),
    shared_totals_by_type: totalsByType(sharedOrbs),
    specific_active_sets: activeSetCounts(specificOrbs),
    specific_totals_by_type: totalsByType(specificOrbs),
    shared_set_bonus_stats: toSortedEntries(sharedSetBonusTotals),
    specific_set_bonus_stats: toSortedEntries(specificSetBonusTotals),
    shared_level_gate_stats: levelGateStatTotals(sharedOrbs),
    specific_level_gate_stats: levelGateStatTotals(specificOrbs),
    shared_with: orderedNumericEntries(sharedWithCounts),
    compromise_loss: compromiseLoss,
    cap_limited_slots: capLimitedSlots,
  };
}
