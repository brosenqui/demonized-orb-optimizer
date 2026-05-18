import { describe, expect, it } from "vitest";
import { initialProfilesState, profilesReducer } from "@/features/profiles/profilesReducer";
import type { OptimizeProfileIn, ShareabilityMatrix } from "@/lib/types";

function profile(
  name: string,
  categories?: Record<string, "Rare" | "Epic" | "Legendary" | "Mythic">
): OptimizeProfileIn {
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
  it("adds and removes profiles while normalizing matrix", () => {
    const withOne = profilesReducer(initialProfilesState, { type: "add_profile" });
    expect(withOne.profiles).toHaveLength(1);
    expect(withOne.shareabilityMatrix.Soul).toBeDefined();

    const removed = profilesReducer(withOne, { type: "remove_profile", index: 0 });
    expect(removed.profiles).toHaveLength(0);
    expect(Object.keys(removed.shareabilityMatrix.Soul ?? {})).toHaveLength(0);
  });

  it("propagates category rarity using matrix-enabled profile cells", () => {
    const matrix: ShareabilityMatrix = {
      Soul: { A: true, B: true, C: false },
    };
    const state = {
      profiles: [profile("A"), profile("B"), profile("C")],
      shareabilityMatrix: matrix,
    };

    const next = profilesReducer(state, {
      type: "set_profile_category",
      index: 0,
      category: "Soul",
      rarity: "Mythic",
    });

    expect(next.profiles[0].categories?.Soul).toBe("Mythic");
    expect(next.profiles[1].categories?.Soul).toBe("Mythic");
    expect(next.profiles[2].categories?.Soul).toBeUndefined();
  });

  it("renames matrix column when profile name changes", () => {
    const state = {
      profiles: [profile("A"), profile("B")],
      shareabilityMatrix: {
        Soul: { A: true, B: false },
      } as ShareabilityMatrix,
    };
    const next = profilesReducer(state, {
      type: "update_profile",
      index: 0,
      profile: profile("Renamed"),
    });

    expect(next.shareabilityMatrix.Soul.Renamed).toBe(true);
    expect(next.shareabilityMatrix.Soul.A).toBeUndefined();
  });

  it("synchronizes category rarity when matrix sharing is enabled", () => {
    const state = {
      profiles: [profile("A", { Soul: "Legendary" }), profile("B", { Soul: "Rare" }), profile("C")],
      shareabilityMatrix: {
        Soul: { A: true, B: false, C: false },
      } as ShareabilityMatrix,
    };

    const next = profilesReducer(state, {
      type: "set_shareability_matrix",
      shareabilityMatrix: {
        Soul: { A: true, B: true, C: false },
      },
    });

    expect(next.profiles[0].categories?.Soul).toBe("Legendary");
    expect(next.profiles[1].categories?.Soul).toBe("Legendary");
    expect(next.profiles[2].categories?.Soul).toBeUndefined();
  });
});
