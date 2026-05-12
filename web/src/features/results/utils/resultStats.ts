import { CATEGORIES } from "@/lib/categoryData";
import type { OrbIn } from "@/lib/types";

export type Assignments = Record<string, OrbIn[]>;

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
