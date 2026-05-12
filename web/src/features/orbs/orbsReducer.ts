import type { OrbIn } from "@/lib/types";

export type OrbsState = {
  orbs: OrbIn[];
};

export type OrbsAction =
  | { type: "hydrate"; orbs: OrbIn[] }
  | { type: "replace"; orbs: OrbIn[] }
  | { type: "add"; orb: OrbIn }
  | { type: "update"; index: number; orb: OrbIn }
  | { type: "remove"; index: number }
  | { type: "clear" };

export const initialOrbsState: OrbsState = {
  orbs: [],
};

export function orbsReducer(state: OrbsState, action: OrbsAction): OrbsState {
  switch (action.type) {
    case "hydrate":
    case "replace":
      return { ...state, orbs: action.orbs };
    case "add":
      return { ...state, orbs: [...state.orbs, action.orb] };
    case "update": {
      const next = [...state.orbs];
      if (action.index < 0 || action.index >= next.length) return state;
      next[action.index] = action.orb;
      return { ...state, orbs: next };
    }
    case "remove":
      return {
        ...state,
        orbs: state.orbs.filter((_, index) => index !== action.index),
      };
    case "clear":
      return { ...state, orbs: [] };
    default:
      return state;
  }
}

export function selectOrbCount(state: OrbsState): number {
  return state.orbs.length;
}
