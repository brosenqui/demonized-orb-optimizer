import { describe, expect, it } from "vitest";
import {
  normalizeShareabilityMatrix,
  propagateCategoryRarity,
  renameProfileInShareabilityMatrix,
  shareabilityMatrixFromLegacy,
  synchronizeCategoryRarityWithMatrix,
  withCategoryRarity,
} from "@/features/profiles/utils/profileHelpers";
import type { OptimizeProfileIn, ShareabilityMatrix } from "@/lib/types";

function makeProfile(
  name: string,
  categories?: Record<string, "Rare" | "Epic" | "Legendary" | "Mythic">
): OptimizeProfileIn {
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

  it("propagates category rarity only across matrix-enabled profiles", () => {
    const profiles = [makeProfile("A"), makeProfile("B"), makeProfile("C")];
    const matrix: ShareabilityMatrix = {
      Soul: { A: true, B: true, C: false },
    };
    const updated = propagateCategoryRarity(profiles, 0, "Soul", "Epic", matrix);

    expect(updated[0].categories?.Soul).toBe("Epic");
    expect(updated[1].categories?.Soul).toBe("Epic");
    expect(updated[2].categories?.Soul).toBeUndefined();
  });

  it("normalizes legacy shareable list to all-profile matrix", () => {
    const profiles = [makeProfile("A"), makeProfile("B")];
    const matrix = shareabilityMatrixFromLegacy(profiles, ["Soul"]);
    expect(matrix.Soul.A).toBe(true);
    expect(matrix.Soul.B).toBe(true);
  });

  it("renames matrix profile keys when profile name changes", () => {
    const matrix: ShareabilityMatrix = {
      Soul: { Old: true, Other: false },
    };
    const renamed = renameProfileInShareabilityMatrix(matrix, "Old", "New");
    expect(renamed.Soul.New).toBe(true);
    expect(renamed.Soul.Old).toBeUndefined();
  });

  it("normalizes matrix shape to categories and current profiles", () => {
    const profiles = [makeProfile("A"), makeProfile("B")];
    const normalized = normalizeShareabilityMatrix(profiles, {
      Soul: { A: true },
    });
    expect(normalized.Soul.A).toBe(true);
    expect(normalized.Soul.B).toBe(false);
    expect(normalized.Wings.A).toBe(false);
  });

  it("synchronizes rarity values across matrix-enabled profiles", () => {
    const profiles = [
      makeProfile("A", { Soul: "Legendary" }),
      makeProfile("B", { Soul: "Rare" }),
      makeProfile("C"),
    ];
    const matrix: ShareabilityMatrix = {
      Soul: { A: true, B: true, C: false },
    };

    const synced = synchronizeCategoryRarityWithMatrix(profiles, matrix);

    expect(synced[0].categories?.Soul).toBe("Legendary");
    expect(synced[1].categories?.Soul).toBe("Legendary");
    expect(synced[2].categories?.Soul).toBeUndefined();
  });

  it("does not force rarity when no enabled profile has a value", () => {
    const profiles = [makeProfile("A"), makeProfile("B"), makeProfile("C", { Soul: "Mythic" })];
    const matrix: ShareabilityMatrix = {
      Soul: { A: true, B: true, C: false },
    };

    const synced = synchronizeCategoryRarityWithMatrix(profiles, matrix);

    expect(synced[0].categories?.Soul).toBeUndefined();
    expect(synced[1].categories?.Soul).toBeUndefined();
    expect(synced[2].categories?.Soul).toBe("Mythic");
  });
});
