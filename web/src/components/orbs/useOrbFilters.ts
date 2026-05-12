import { useMemo, useState } from "react";
import type { OrbIn } from "../../lib/types";
import { ORB_SETS, ORB_TYPES } from "../../lib/orbData";

const DEFAULT_LEVEL_MIN = 0;
const DEFAULT_LEVEL_MAX = 9;

function buildOrderIndex(catalog: readonly string[], selected: string[]) {
  const seen = new Set<string>();
  const order: string[] = [];
  for (const value of selected) {
    if (!seen.has(value)) {
      seen.add(value);
      order.push(value);
    }
  }
  for (const value of catalog) {
    if (!seen.has(value)) {
      seen.add(value);
      order.push(value);
    }
  }
  return new Map(order.map((value, index) => [value, index]));
}

function rarityRank(rarity: OrbIn["rarity"]) {
  if (rarity === "Mythic") return 5;
  if (rarity === "Legendary") return 4;
  if (rarity === "Epic") return 3;
  if (rarity === "Rare") return 2;
  if (rarity === "Magic") return 1;
  if (rarity === "Common") return 0;
  return -1;
}

export function useOrbFilters(orbs: OrbIn[]) {
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedSets, setSelectedSets] = useState<string[]>([]);
  const [selectedRarities, setSelectedRarities] = useState<string[]>([]);
  const [levelMin, setLevelMin] = useState(DEFAULT_LEVEL_MIN);
  const [levelMax, setLevelMax] = useState(DEFAULT_LEVEL_MAX);
  const [searchQuery, setSearchQuery] = useState("");

  const visibleOrbIndices = useMemo(() => {
    const typeIdx = buildOrderIndex(ORB_TYPES, selectedTypes);
    const setIdx = buildOrderIndex(ORB_SETS, selectedSets);
    const raritySet = new Set(selectedRarities);
    const normalizedSearchQuery = searchQuery.trim().toLowerCase();
    const typeSet = new Set(selectedTypes);
    const setSet = new Set(selectedSets);

    const decorated = orbs
      .map((orb, index) => ({ orb, index }))
      .filter(({ orb }) => {
        const typeOk = typeSet.size === 0 || typeSet.has(orb.type);
        const setOk = setSet.size === 0 || setSet.has(orb.set);
        const rarityOk = raritySet.size === 0 || raritySet.has(orb.rarity);
        const levelOk = orb.level >= levelMin && orb.level <= levelMax;
        const searchOk =
          normalizedSearchQuery === "" ||
          `${orb.type} ${orb.set} ${orb.rarity} awakened ${orb.awakened}`
            .toLowerCase()
            .includes(normalizedSearchQuery);
        return typeOk && setOk && rarityOk && levelOk && searchOk;
      });

    decorated.sort((left, right) => {
      const orbA = left.orb;
      const orbB = right.orb;

      const typeOrderA = typeIdx.get(orbA.type) ?? Number.MAX_SAFE_INTEGER;
      const typeOrderB = typeIdx.get(orbB.type) ?? Number.MAX_SAFE_INTEGER;
      if (typeOrderA !== typeOrderB) return typeOrderA - typeOrderB;

      const rarityOrderA = rarityRank(orbA.rarity);
      const rarityOrderB = rarityRank(orbB.rarity);
      if (rarityOrderA !== rarityOrderB) return rarityOrderB - rarityOrderA;

      if (orbA.level !== orbB.level) return orbB.level - orbA.level;

      if (orbA.awakened !== orbB.awakened) return orbB.awakened - orbA.awakened;

      const setOrderA = setIdx.get(orbA.set) ?? Number.MAX_SAFE_INTEGER;
      const setOrderB = setIdx.get(orbB.set) ?? Number.MAX_SAFE_INTEGER;
      if (setOrderA !== setOrderB) return setOrderA - setOrderB;

      if (orbA.value !== orbB.value) return orbB.value - orbA.value;

      return left.index - right.index;
    });

    return decorated.map((entry) => entry.index);
  }, [orbs, selectedTypes, selectedSets, selectedRarities, levelMin, levelMax, searchQuery]);

  const visibleOrbs = useMemo(
    () => visibleOrbIndices.map((index) => orbs[index]),
    [visibleOrbIndices, orbs]
  );

  const hasActiveFilters =
    selectedTypes.length > 0 ||
    selectedSets.length > 0 ||
    selectedRarities.length > 0 ||
    levelMin > DEFAULT_LEVEL_MIN ||
    levelMax < DEFAULT_LEVEL_MAX ||
    searchQuery.trim() !== "";

  const activeFilterGroups = [
    selectedTypes.length > 0,
    selectedSets.length > 0,
    selectedRarities.length > 0,
    levelMin > DEFAULT_LEVEL_MIN || levelMax < DEFAULT_LEVEL_MAX,
    searchQuery.trim() !== "",
  ].filter(Boolean).length;

  function resetFilters() {
    setSelectedTypes([]);
    setSelectedSets([]);
    setSelectedRarities([]);
    setLevelMin(DEFAULT_LEVEL_MIN);
    setLevelMax(DEFAULT_LEVEL_MAX);
    setSearchQuery("");
  }

  return {
    selectedTypes,
    setSelectedTypes,
    selectedSets,
    setSelectedSets,
    selectedRarities,
    setSelectedRarities,
    levelMin,
    setLevelMin,
    levelMax,
    setLevelMax,
    searchQuery,
    setSearchQuery,
    visibleOrbIndices,
    visibleOrbs,
    hasActiveFilters,
    activeFilterGroups,
    resetFilters,
  };
}
