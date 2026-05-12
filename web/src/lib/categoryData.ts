import { categoryRarityOptions, type CategoryRarity } from "@/lib/types";

export const CATEGORIES = ["Soul", "Wings", "Ego", "Beast", "Wagon", "Spirit Souls"] as const;

export type CategoryName = (typeof CATEGORIES)[number];

export const CATEGORY_RARITY_CHOICES = categoryRarityOptions;

export const CATEGORY_RARITY_SLOTS: Record<CategoryRarity, number> = {
  Rare: 1,
  Epic: 2,
  Legendary: 3,
  Mythic: 4,
};

export function slotsForRarity(rarity: CategoryRarity): number {
  return CATEGORY_RARITY_SLOTS[rarity];
}

export function normalizeCategoryRarity(rarity?: string): CategoryRarity {
  if (!rarity) return "Rare";
  return CATEGORY_RARITY_CHOICES.find((value) => value === rarity) ?? "Rare";
}
