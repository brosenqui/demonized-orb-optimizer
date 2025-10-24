export const RARITY_LEVEL_CAP: Record<string, number> = {
  Common: 3,
  Magic: 3,
  Rare: 6,
  Epic: 6,
  Legendary: 9,
  Mythic: 9,
};

export function clampLevel(rarity: string, level: number) {
  const max = RARITY_LEVEL_CAP[rarity] ?? 9;
  if (Number.isNaN(level)) return 0;
  return Math.min(Math.max(0, Math.floor(level)), max);
}

export function clampNonNegative(n: number) {
  if (Number.isNaN(n)) return 0;
  return Math.max(0, n);
}
