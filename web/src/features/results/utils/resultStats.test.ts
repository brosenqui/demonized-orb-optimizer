import { describe, expect, it } from "vitest";
import {
  activeSetCounts,
  flattenAssignments,
  levelGateStatTotals,
  orderedCategories,
  sharedStatsForProfile,
  totalsByType,
} from "@/features/results/utils/resultStats";
import type { OrbIn } from "@/lib/types";

const FLAME: OrbIn = {
  type: "Flame",
  set: "Lucifer",
  rarity: "Rare",
  value: 10,
  level: 1,
  awakened: 0,
};
const WATER: OrbIn = {
  type: "Water",
  set: "Mammon",
  rarity: "Epic",
  value: 5,
  level: 2,
  awakened: 1,
};

const FLAME_L6_AWAKENED: OrbIn = {
  type: "Flame",
  set: "Lucifer",
  rarity: "Legendary",
  value: 12,
  level: 6,
  awakened: 9,
};

const EARTH_L9: OrbIn = {
  type: "Earth",
  set: "Leviathan",
  rarity: "Legendary",
  value: 8,
  level: 9,
  awakened: 0,
};

const LUCIFER_ORB: OrbIn = {
  type: "Wind",
  set: "Lucifer",
  rarity: "Legendary",
  value: 10,
  level: 1,
  awakened: 0,
};

describe("resultStats", () => {
  it("orders known categories using canonical category order", () => {
    const ordered = orderedCategories({
      Wagon: [FLAME],
      Soul: [WATER],
      Unknown: [],
    });

    expect(ordered[0]).toBe("Soul");
    expect(ordered[1]).toBe("Wagon");
    expect(ordered[2]).toBe("Unknown");
  });

  it("flattens assignments", () => {
    const flattened = flattenAssignments({
      Soul: [FLAME],
      Wings: [WATER],
    });
    expect(flattened).toHaveLength(2);
  });

  it("computes set counts and type totals", () => {
    const orbs = [FLAME, FLAME, WATER];
    const sets = activeSetCounts(orbs);
    const types = totalsByType(orbs);

    expect(sets[0]).toEqual(["Lucifer", 2]);
    expect(types[0]).toEqual(["Flame", 20]);
  });

  it("computes level-gate stats cumulatively from base level only", () => {
    const totals = levelGateStatTotals([
      FLAME_L6_AWAKENED,
      EARTH_L9,
      { ...WATER, level: 2, awakened: 99 },
    ]);
    expect(totals).toContainEqual(["Normal ATK Amp %", 225]);
    expect(totals).toContainEqual(["HP %", 120]);
    expect(totals.some(([stat]) => stat === "Resurrection Chance %")).toBe(false);
  });

  it("splits level-gate stats into shared and profile-only buckets", () => {
    const assignments = {
      Soul: [FLAME_L6_AWAKENED],
      Wagon: [EARTH_L9],
    };
    const sharedSummary = {
      active_sets: {},
      totals_by_type: {},
      compromise_loss_total: 0,
      compromise_loss_by_profile: {},
      cap_limited_slots_by_profile: {},
      slots: [
        {
          category: "Soul",
          slot_index: 0,
          profiles: ["P1", "P2"],
          is_uniform: true,
          orb: FLAME_L6_AWAKENED,
          profile_orbs: { P1: FLAME_L6_AWAKENED, P2: FLAME_L6_AWAKENED },
          profile_impacts: [],
        },
      ],
    };
    const stats = sharedStatsForProfile(assignments, sharedSummary, "P1");
    expect(stats.shared_level_gate_stats).toContainEqual(["Normal ATK Amp %", 225]);
    expect(stats.specific_level_gate_stats).toContainEqual(["HP %", 120]);
  });

  it("splits set tier bonuses using shared baseline and total unlocks", () => {
    const assignments = {
      Soul: [
        { ...LUCIFER_ORB, type: "Flame", slot_index: 0 },
        { ...LUCIFER_ORB, type: "Water", slot_index: 1 },
        { ...LUCIFER_ORB, type: "Wind", slot_index: 2 },
        { ...LUCIFER_ORB, type: "Earth", slot_index: 3 },
        { ...LUCIFER_ORB, type: "Sun", slot_index: 4 },
        { ...LUCIFER_ORB, type: "Grass", slot_index: 5 },
      ],
    };
    const sharedSummary = {
      active_sets: {},
      totals_by_type: {},
      compromise_loss_total: 0,
      compromise_loss_by_profile: {},
      cap_limited_slots_by_profile: {},
      slots: [0, 1, 2, 3].map((slot) => ({
        category: "Soul",
        slot_index: slot,
        profiles: ["P1", "P2"],
        is_uniform: true,
        orb: assignments.Soul[slot],
        profile_orbs: { P1: assignments.Soul[slot], P2: assignments.Soul[slot] },
        profile_impacts: [],
      })),
    };
    const stats = sharedStatsForProfile(assignments, sharedSummary, "P1");
    expect(stats.shared_set_bonus_stats).toContainEqual(["Stun Chance %", 2]);
    expect(stats.specific_set_bonus_stats).toContainEqual(["Stun Chance %", 1]);
  });
});
