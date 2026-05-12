import type { OptimizeResponse } from "@/lib/types";

export type RunStatus = "idle" | "loading" | "success" | "error";

export type RunState = {
  status: RunStatus;
  loading: boolean;
  error: string | null;
  result: OptimizeResponse | null;
};

export type RunAction =
  | { type: "start" }
  | { type: "success"; result: OptimizeResponse }
  | { type: "error"; error: string }
  | { type: "reset" };

export const initialRunState: RunState = {
  status: "idle",
  loading: false,
  error: null,
  result: null,
};

export function runReducer(state: RunState, action: RunAction): RunState {
  switch (action.type) {
    case "start":
      return {
        ...state,
        status: "loading",
        loading: true,
        error: null,
      };
    case "success":
      return {
        ...state,
        status: "success",
        loading: false,
        error: null,
        result: action.result,
      };
    case "error":
      return {
        ...state,
        status: "error",
        loading: false,
        error: action.error,
      };
    case "reset":
      return initialRunState;
    default:
      return state;
  }
}
