import { PROFILE_DEFAULTS } from "@/lib/priorityTemplates";
import type { CategoryRarity, OptimizeProfileIn, ShareabilityMatrix } from "@/lib/types";
import {
  normalizeShareabilityMatrix,
  propagateCategoryRarity,
  renameProfileInShareabilityMatrix,
  synchronizeCategoryRarityWithMatrix,
} from "@/features/profiles/utils/profileHelpers";

export type ProfilesState = {
  profiles: OptimizeProfileIn[];
  shareabilityMatrix: ShareabilityMatrix;
};

export type ProfilesAction =
  | { type: "hydrate"; profiles: OptimizeProfileIn[]; shareabilityMatrix: ShareabilityMatrix }
  | { type: "set_profiles"; profiles: OptimizeProfileIn[] }
  | { type: "set_shareability_matrix"; shareabilityMatrix: ShareabilityMatrix }
  | { type: "add_profile" }
  | { type: "update_profile"; index: number; profile: OptimizeProfileIn }
  | { type: "remove_profile"; index: number }
  | { type: "set_profile_category"; index: number; category: string; rarity: CategoryRarity | "" };

export const initialProfilesState: ProfilesState = {
  profiles: [],
  shareabilityMatrix: {},
};

function withNormalizedMatrix(
  profiles: OptimizeProfileIn[],
  matrix: ShareabilityMatrix
): ProfilesState {
  const normalizedMatrix = normalizeShareabilityMatrix(profiles, matrix);
  return {
    profiles: synchronizeCategoryRarityWithMatrix(profiles, normalizedMatrix),
    shareabilityMatrix: normalizedMatrix,
  };
}

export function profilesReducer(state: ProfilesState, action: ProfilesAction): ProfilesState {
  switch (action.type) {
    case "hydrate":
      return withNormalizedMatrix(action.profiles, action.shareabilityMatrix);
    case "set_profiles":
      return withNormalizedMatrix(action.profiles, state.shareabilityMatrix);
    case "set_shareability_matrix":
      return withNormalizedMatrix(state.profiles, action.shareabilityMatrix);
    case "add_profile": {
      const nextProfiles = [...state.profiles, { ...PROFILE_DEFAULTS }];
      return withNormalizedMatrix(nextProfiles, state.shareabilityMatrix);
    }
    case "update_profile": {
      const nextProfiles = [...state.profiles];
      if (action.index < 0 || action.index >= nextProfiles.length) return state;
      const previousProfile = nextProfiles[action.index];
      const renamedMatrix = renameProfileInShareabilityMatrix(
        state.shareabilityMatrix,
        previousProfile.name,
        action.profile.name
      );
      nextProfiles[action.index] = action.profile;
      return withNormalizedMatrix(nextProfiles, renamedMatrix);
    }
    case "remove_profile": {
      const nextProfiles = state.profiles.filter((_, index) => index !== action.index);
      return withNormalizedMatrix(nextProfiles, state.shareabilityMatrix);
    }
    case "set_profile_category":
      return {
        ...state,
        profiles: propagateCategoryRarity(
          state.profiles,
          action.index,
          action.category,
          action.rarity,
          state.shareabilityMatrix
        ),
      };
    default:
      return state;
  }
}
