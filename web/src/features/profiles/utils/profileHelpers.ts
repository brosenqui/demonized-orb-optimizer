import type { CategoryRarity, OptimizeProfileIn } from "@/lib/types";

export function sanitizeNumber(value: number, fallback = 0): number {
  if (!Number.isFinite(value)) return fallback;
  return value;
}

export function withCategoryRarity(
  profile: OptimizeProfileIn,
  category: string,
  rarity: CategoryRarity | ""
): OptimizeProfileIn {
  const current = { ...(profile.categories ?? {}) };
  if (rarity === "") {
    delete current[category];
  } else {
    current[category] = rarity;
  }
  return { ...profile, categories: current };
}

export function propagateCategoryRarity(
  profiles: OptimizeProfileIn[],
  targetIndex: number,
  category: string,
  rarity: CategoryRarity | "",
  shareable: string[]
): OptimizeProfileIn[] {
  const updated = profiles.map((profile, index) =>
    index === targetIndex ? withCategoryRarity(profile, category, rarity) : profile
  );

  if (!shareable.includes(category)) return updated;

  return updated.map((profile) => withCategoryRarity(profile, category, rarity));
}

export function synchronizeShareableCategories(
  profiles: OptimizeProfileIn[],
  shareable: readonly string[]
): OptimizeProfileIn[] {
  if (profiles.length <= 1 || shareable.length === 0) return profiles;

  let next = [...profiles];
  for (const category of shareable) {
    const firstDefined = next
      .map((profile) => profile.categories?.[category])
      .find((value): value is CategoryRarity => value !== undefined);

    if (!firstDefined) continue;
    next = next.map((profile) => withCategoryRarity(profile, category, firstDefined));
  }
  return next;
}
