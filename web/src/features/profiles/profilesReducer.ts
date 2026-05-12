import { PROFILE_DEFAULTS } from "@/lib/priorityTemplates";
import type { CategoryRarity, OptimizeProfileIn } from "@/lib/types";
import {
  propagateCategoryRarity,
  synchronizeShareableCategories,
} from "@/features/profiles/utils/profileHelpers";

export type ProfilesState = {
  profiles: OptimizeProfileIn[];
  shareable: string[];
};

export type ProfilesAction =
  | { type: "hydrate"; profiles: OptimizeProfileIn[]; shareable: string[] }
  | { type: "set_profiles"; profiles: OptimizeProfileIn[] }
  | { type: "set_shareable"; shareable: string[] }
  | { type: "add_profile" }
  | { type: "update_profile"; index: number; profile: OptimizeProfileIn }
  | { type: "remove_profile"; index: number }
  | { type: "set_profile_category"; index: number; category: string; rarity: CategoryRarity | "" };

export const initialProfilesState: ProfilesState = {
  profiles: [],
  shareable: [],
};

export function profilesReducer(state: ProfilesState, action: ProfilesAction): ProfilesState {
  switch (action.type) {
    case "hydrate":
      return { profiles: action.profiles, shareable: action.shareable };
    case "set_profiles":
      return { ...state, profiles: action.profiles };
    case "set_shareable":
      return {
        ...state,
        shareable: action.shareable,
        profiles: synchronizeShareableCategories(state.profiles, action.shareable),
      };
    case "add_profile":
      return {
        ...state,
        profiles: [...state.profiles, { ...PROFILE_DEFAULTS }],
      };
    case "update_profile": {
      const next = [...state.profiles];
      if (action.index < 0 || action.index >= next.length) return state;
      next[action.index] = action.profile;
      return { ...state, profiles: next };
    }
    case "remove_profile":
      return {
        ...state,
        profiles: state.profiles.filter((_, index) => index !== action.index),
      };
    case "set_profile_category":
      return {
        ...state,
        profiles: propagateCategoryRarity(
          state.profiles,
          action.index,
          action.category,
          action.rarity,
          state.shareable
        ),
      };
    default:
      return state;
  }
}
