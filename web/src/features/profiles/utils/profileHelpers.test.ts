import { describe, expect, it } from "vitest";
import {
  propagateCategoryRarity,
  synchronizeShareableCategories,
  withCategoryRarity,
} from "@/features/profiles/utils/profileHelpers";
import type { OptimizeProfileIn } from "@/lib/types";

function makeProfile(name: string, categories?: Record<string, "Rare" | "Epic" | "Legendary" | "Mythic">): OptimizeProfileIn {
  return {
    name,
    weight: 1,
    objective: "sets-first",
    power: 1,
    epsilon: 0.01,
    set_priority: {},
    orb_weights: {},
    orb_level_weights: {},
    categories,
  };
}

describe("profileHelpers", () => {
  it("sets and clears category rarity", () => {
    const base = makeProfile("A", { Soul: "Rare" });
    const updated = withCategoryRarity(base, "Soul", "Mythic");
    const cleared = withCategoryRarity(updated, "Soul", "");

    expect(updated.categories?.Soul).toBe("Mythic");
    expect(cleared.categories?.Soul).toBeUndefined();
  });

  it("propagates category rarity only when category is shareable", () => {
    const profiles = [makeProfile("A"), makeProfile("B")];
    const nonShareable = propagateCategoryRarity(profiles, 0, "Soul", "Epic", []);
    const shareable = propagateCategoryRarity(profiles, 0, "Soul", "Epic", ["Soul"]);

    expect(nonShareable[0].categories?.Soul).toBe("Epic");
    expect(nonShareable[1].categories?.Soul).toBeUndefined();

    expect(shareable[0].categories?.Soul).toBe("Epic");
    expect(shareable[1].categories?.Soul).toBe("Epic");
  });

  it("synchronizes already-defined shareable categories across profiles", () => {
    const profiles = [
      makeProfile("A", { Soul: "Legendary" }),
      makeProfile("B", { Soul: "Rare", Wings: "Epic" }),
      makeProfile("C"),
    ];

    const synchronized = synchronizeShareableCategories(profiles, ["Soul", "Wings"]);
    expect(synchronized[0].categories?.Soul).toBe("Legendary");
    expect(synchronized[1].categories?.Soul).toBe("Legendary");
    expect(synchronized[2].categories?.Soul).toBe("Legendary");
    expect(synchronized[2].categories?.Wings).toBe("Epic");
  });
});
