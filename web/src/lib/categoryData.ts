// Canonical categories for the optimizer UI
export const CATEGORIES = ["Soul", "Wings", "Ego", "Beast", "Wagon"] as const;

// Category rarity choices (categories don't use Common/Magic)
export const CATEGORY_RARITY_CHOICES = ["Rare", "Epic", "Legendary", "Mythic"] as const;

// Slots per rarity (for categories)
export const CATEGORY_RARITY_SLOTS: Record<(typeof CATEGORY_RARITY_CHOICES)[number], number> = {
  Rare: 1,
  Epic: 2,
  Legendary: 3,
  Mythic: 4,
};

// Helpers
export function slotsForRarity(rarity: string): number {
  return CATEGORY_RARITY_SLOTS[rarity as keyof typeof CATEGORY_RARITY_SLOTS] ?? 0;
}

export function normalizeCategoryRarity(rarity?: string): (typeof CATEGORY_RARITY_CHOICES)[number] {
  if (!rarity || !CATEGORY_RARITY_CHOICES.includes(rarity as any)) return "Rare";
  return rarity as any;
}
