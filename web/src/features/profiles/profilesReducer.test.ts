import { describe, expect, it } from "vitest";
import { initialProfilesState, profilesReducer } from "@/features/profiles/profilesReducer";
import type { OptimizeProfileIn } from "@/lib/types";

function profile(name: string, categories?: Record<string, "Rare" | "Epic" | "Legendary" | "Mythic">): OptimizeProfileIn {
  return {
    name,
    weight: 1,
    objective: "sets-first",
    power: 2,
    epsilon: 0.02,
    set_priority: {},
    orb_weights: {},
    orb_level_weights: {},
    categories,
  };
}

describe("profilesReducer", () => {
  it("adds and removes profiles", () => {
    const withOne = profilesReducer(initialProfilesState, { type: "add_profile" });
    expect(withOne.profiles).toHaveLength(1);

    const removed = profilesReducer(withOne, { type: "remove_profile", index: 0 });
    expect(removed.profiles).toHaveLength(0);
  });

  it("propagates shareable category changes", () => {
    const state = {
      profiles: [profile("A"), profile("B")],
      shareable: ["Soul"],
    };

    const next = profilesReducer(state, {
      type: "set_profile_category",
      index: 0,
      category: "Soul",
      rarity: "Mythic",
    });

    expect(next.profiles[0].categories?.Soul).toBe("Mythic");
    expect(next.profiles[1].categories?.Soul).toBe("Mythic");
  });

  it("synchronizes existing values when shareable list changes", () => {
    const state = {
      profiles: [profile("A", { Soul: "Legendary" }), profile("B", { Soul: "Rare" })],
      shareable: [],
    };

    const next = profilesReducer(state, {
      type: "set_shareable",
      shareable: ["Soul"],
    });

    expect(next.profiles[0].categories?.Soul).toBe("Legendary");
    expect(next.profiles[1].categories?.Soul).toBe("Legendary");
  });
});
