import { CATEGORIES } from "@/lib/categoryData";
import type { CategoryRarity, OptimizeProfileIn, ShareabilityMatrix } from "@/lib/types";

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

export function normalizeShareabilityMatrix(
  profiles: OptimizeProfileIn[],
  matrix: ShareabilityMatrix | null | undefined
): ShareabilityMatrix {
  const normalized: ShareabilityMatrix = {};
  for (const category of CATEGORIES) {
    const row = matrix?.[category] ?? {};
    normalized[category] = {};
    for (const profile of profiles) {
      normalized[category][profile.name] = Boolean(row[profile.name]);
    }
  }
  return normalized;
}

export function shareabilityMatrixFromLegacy(
  profiles: OptimizeProfileIn[],
  shareableCategories: readonly string[] | null | undefined
): ShareabilityMatrix {
  const selected = new Set((shareableCategories ?? []).map((category) => String(category)));
  const matrix: ShareabilityMatrix = {};
  for (const category of CATEGORIES) {
    matrix[category] = {};
    for (const profile of profiles) {
      matrix[category][profile.name] = selected.has(category);
    }
  }
  return matrix;
}

export function renameProfileInShareabilityMatrix(
  matrix: ShareabilityMatrix,
  previousName: string,
  nextName: string
): ShareabilityMatrix {
  if (!previousName || !nextName || previousName === nextName) return matrix;
  const updated: ShareabilityMatrix = {};
  for (const [category, row] of Object.entries(matrix)) {
    const nextRow: Record<string, boolean> = {};
    for (const [profileName, enabled] of Object.entries(row)) {
      if (profileName === previousName) {
        nextRow[nextName] = enabled;
      } else {
        nextRow[profileName] = enabled;
      }
    }
    updated[category] = nextRow;
  }
  return updated;
}

export function propagateCategoryRarity(
  profiles: OptimizeProfileIn[],
  targetIndex: number,
  category: string,
  rarity: CategoryRarity | "",
  matrix: ShareabilityMatrix
): OptimizeProfileIn[] {
  const updated = profiles.map((profile, index) =>
    index === targetIndex ? withCategoryRarity(profile, category, rarity) : profile
  );
  const sourceProfile = updated[targetIndex];
  if (!sourceProfile) return updated;
  if (!matrix?.[category]?.[sourceProfile.name]) return updated;

  return updated.map((profile, index) => {
    if (index === targetIndex) return profile;
    if (!matrix?.[category]?.[profile.name]) return profile;
    return withCategoryRarity(profile, category, rarity);
  });
}

export function synchronizeCategoryRarityWithMatrix(
  profiles: OptimizeProfileIn[],
  matrix: ShareabilityMatrix
): OptimizeProfileIn[] {
  let nextProfiles = profiles;
  let changed = false;

  for (const category of CATEGORIES) {
    const enabledIndexes: number[] = [];
    for (let index = 0; index < nextProfiles.length; index += 1) {
      const profile = nextProfiles[index];
      if (matrix?.[category]?.[profile.name]) {
        enabledIndexes.push(index);
      }
    }

    if (enabledIndexes.length < 2) continue;

    let canonicalRarity: CategoryRarity | undefined;
    for (const index of enabledIndexes) {
      const rarity = nextProfiles[index].categories?.[category];
      if (rarity) {
        canonicalRarity = rarity;
        break;
      }
    }

    if (!canonicalRarity) continue;

    for (const index of enabledIndexes) {
      const profile = nextProfiles[index];
      if (profile.categories?.[category] === canonicalRarity) continue;

      if (!changed) {
        nextProfiles = [...nextProfiles];
        changed = true;
      }

      nextProfiles[index] = withCategoryRarity(profile, category, canonicalRarity);
    }
  }

  return nextProfiles;
}
