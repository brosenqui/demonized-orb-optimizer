import { describe, expect, it } from "vitest";
import {
  activeSetCounts,
  flattenAssignments,
  orderedCategories,
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
});
