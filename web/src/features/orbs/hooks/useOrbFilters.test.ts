import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useOrbFilters } from "@/features/orbs/hooks/useOrbFilters";
import type { OrbIn } from "@/lib/types";

const ORBS: OrbIn[] = [
  { type: "Flame", set: "Lucifer", rarity: "Rare", value: 10, level: 3, awakened: 0 },
  { type: "Flame", set: "Mammon", rarity: "Rare", value: 12, level: 3, awakened: 2 },
  { type: "Water", set: "Mammon", rarity: "Mythic", value: 25, level: 5, awakened: 0 },
  { type: "Steel", set: "Satan", rarity: "Magic", value: 5, level: 1, awakened: 0 },
];

describe("useOrbFilters", () => {
  it("filters by selected type", () => {
    const { result } = renderHook(() => useOrbFilters(ORBS));

    act(() => {
      result.current.setSelectedTypes(["Flame"]);
    });

    expect(result.current.visibleOrbs).toHaveLength(2);
    expect(result.current.visibleOrbs.every((orb) => orb.type === "Flame")).toBe(true);
  });

  it("orders equal rarity/level by awakened descending", () => {
    const { result } = renderHook(() => useOrbFilters(ORBS));

    act(() => {
      result.current.setSelectedTypes(["Flame"]);
      result.current.setSelectedRarities(["Rare"]);
      result.current.setLevelMin(3);
      result.current.setLevelMax(3);
    });

    expect(result.current.visibleOrbs[0].awakened).toBe(2);
    expect(result.current.visibleOrbs[1].awakened).toBe(0);
  });

  it("supports text search across type/set/rarity/awakened", () => {
    const { result } = renderHook(() => useOrbFilters(ORBS));

    act(() => {
      result.current.setSearchQuery("awakened 2");
    });

    expect(result.current.visibleOrbs).toHaveLength(1);
    expect(result.current.visibleOrbs[0].set).toBe("Mammon");
  });

  it("resets filter state and active flags", () => {
    const { result } = renderHook(() => useOrbFilters(ORBS));

    act(() => {
      result.current.setSelectedSets(["Mammon"]);
      result.current.setSearchQuery("Rare");
    });

    expect(result.current.hasActiveFilters).toBe(true);

    act(() => {
      result.current.resetFilters();
    });

    expect(result.current.hasActiveFilters).toBe(false);
    expect(result.current.visibleOrbs).toHaveLength(ORBS.length);
  });
});
