type SetTierBonuses = Record<string, Record<number, Record<string, number>>>;

export const SET_TIER_BONUSES: SetTierBonuses = {
  Lucifer: {
    4: { "Stun Chance %": 2 },
    5: { "Stun Chance %": 2.5 },
    6: { "Stun Chance %": 3 },
  },
  Mammon: {
    2: { "Set ATK %": 300 },
    4: { "Set ATK %": 550 },
    6: { "Set ATK %": 1000 },
  },
  Leviathan: {
    3: { "Set HP %": 25 },
    5: { "Set HP %": 50 },
    6: { "Set HP %": 100 },
  },
  Satan: {
    4: { "Silence Chance %": 1.5 },
    5: { "Silence Chance %": 2 },
    6: { "Silence Chance %": 2.5 },
  },
  Asmodeus: {
    2: { "Set Accuracy %": 50 },
    4: { "Set Accuracy %": 100 },
  },
  Beelzebub: {
    1: { "Mythic Skill Damage Amp %": 50 },
    3: { "Mythic Skill Damage Amp %": 100 },
    5: { "Mythic Skill Damage Amp %": 200 },
  },
  Belphegor: {
    2: { "Passive Skill Amplification %": 5 },
    4: { "Passive Skill Amplification %": 10 },
    6: { "Passive Skill Amplification %": 15 },
  },
};

export type HighestSetTierBonus = {
  threshold: number;
  bonusByStat: Record<string, number>;
};

export function highestSetTierBonus(setName: string, count: number): HighestSetTierBonus | null {
  const tiers = SET_TIER_BONUSES[setName];
  if (!tiers) return null;
  const unlockedThresholds = Object.keys(tiers)
    .map((thresholdRaw) => Number(thresholdRaw))
    .filter((threshold) => Number.isFinite(threshold) && count >= threshold)
    .sort((left, right) => right - left);
  if (unlockedThresholds.length === 0) return null;
  const threshold = unlockedThresholds[0];
  const bonusByStat = tiers[threshold];
  if (!bonusByStat) return null;
  return { threshold, bonusByStat };
}

export function setBonusTotalsFromCounts(setCounts: Map<string, number>): Map<string, number> {
  const totals = new Map<string, number>();

  for (const [setName, count] of setCounts.entries()) {
    const highest = highestSetTierBonus(setName, count);
    if (!highest) continue;
    const bonusByStat = highest.bonusByStat;

    for (const [statName, value] of Object.entries(bonusByStat)) {
      if (!Number.isFinite(value)) continue;
      totals.set(statName, (totals.get(statName) ?? 0) + value);
    }
  }

  return totals;
}
