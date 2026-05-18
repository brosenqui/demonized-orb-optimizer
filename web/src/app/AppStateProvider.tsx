import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
} from "react";
import { toast } from "sonner";
import { z } from "zod";
import { postOptimize } from "@/lib/api";
import { clearState, loadState, saveState } from "@/lib/persist";
import { optimizeProfileInSchema, orbInSchema } from "@/lib/schemas";
import type {
  CategoryRarity,
  OptimizeProfileIn,
  OptimizeRequest,
  OptimizeResponse,
  OrbIn,
  ShareabilityMatrix,
} from "@/lib/types";
import { orbsReducer, initialOrbsState } from "@/features/orbs/orbsReducer";
import { initialProfilesState, profilesReducer } from "@/features/profiles/profilesReducer";
import {
  normalizeShareabilityMatrix,
  shareabilityMatrixFromLegacy,
} from "@/features/profiles/utils/profileHelpers";
import { initialRunState, runReducer } from "./runReducer";

export type SavedState = {
  orbs: OrbIn[];
  profiles: OptimizeProfileIn[];
  shareability_matrix: ShareabilityMatrix;
  shareable?: string[];
};

const savedStateSchema = z.object({
  orbs: z.array(orbInSchema).default([]),
  profiles: z.array(optimizeProfileInSchema).default([]),
  shareability_matrix: z
    .record(z.string(), z.record(z.string(), z.boolean()))
    .optional(),
  shareable: z.array(z.string()).optional(),
});

type AppStateContextValue = {
  orbs: OrbIn[];
  profiles: OptimizeProfileIn[];
  shareabilityMatrix: ShareabilityMatrix;
  loading: boolean;
  error: string | null;
  result: OptimizeResponse | null;
  payload: OptimizeRequest;
  setOrbs: (orbs: OrbIn[]) => void;
  setShareabilityMatrix: (shareabilityMatrix: ShareabilityMatrix) => void;
  addProfile: () => void;
  updateProfile: (index: number, profile: OptimizeProfileIn) => void;
  removeProfile: (index: number) => void;
  setProfileCategory: (index: number, category: string, rarity: CategoryRarity | "") => void;
  runOptimize: () => Promise<void>;
  saveSetup: () => void;
  clearSavedSetup: () => void;
  copySetupJson: () => Promise<void>;
};

const AppStateContext = createContext<AppStateContextValue | null>(null);

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [orbsState, orbsDispatch] = useReducer(orbsReducer, initialOrbsState);
  const [profilesState, profilesDispatch] = useReducer(profilesReducer, initialProfilesState);
  const [runState, runDispatch] = useReducer(runReducer, initialRunState);

  useEffect(() => {
    const saved = loadState<unknown>();
    if (!saved) return;

    const parsed = savedStateSchema.safeParse(saved);
    if (!parsed.success) {
      clearState();
      toast.error("Saved setup was invalid and has been cleared.");
      return;
    }

    const restored = parsed.data;
    const migratedMatrix = restored.shareability_matrix
      ? normalizeShareabilityMatrix(restored.profiles, restored.shareability_matrix)
      : shareabilityMatrixFromLegacy(restored.profiles, restored.shareable);
    orbsDispatch({ type: "hydrate", orbs: restored.orbs });
    profilesDispatch({
      type: "hydrate",
      profiles: restored.profiles,
      shareabilityMatrix: migratedMatrix,
    });
    toast.success("Restored your saved setup.");
  }, []);

  const payload = useMemo<OptimizeRequest>(
    () => {
      const categoriesInProfiles = new Set<string>();
      for (const profile of profilesState.profiles) {
        for (const category of Object.keys(profile.categories ?? {})) {
          categoriesInProfiles.add(category);
        }
      }

      const matrixForPayload: ShareabilityMatrix = {};
      for (const category of categoriesInProfiles) {
        const row: Record<string, boolean> = {};
        for (const profile of profilesState.profiles) {
          row[profile.name] = Boolean(profilesState.shareabilityMatrix?.[category]?.[profile.name]);
        }
        matrixForPayload[category] = row;
      }

      return {
        orbs: orbsState.orbs,
        profiles: profilesState.profiles,
        shareability_matrix: matrixForPayload,
        algorithm: "greedy",
      };
    },
    [orbsState.orbs, profilesState.profiles, profilesState.shareabilityMatrix]
  );

  const runOptimize = useCallback(async () => {
    if (payload.orbs.length === 0) {
      toast.error("Add at least one orb before running optimization.");
      return;
    }
    if (payload.profiles.length === 0) {
      toast.error("Add at least one profile before running optimization.");
      return;
    }

    runDispatch({ type: "start" });
    const toastId = toast.loading("Running optimizer…");

    try {
      const data = await postOptimize(payload);
      runDispatch({ type: "success", result: data });
      toast.success("Optimization complete.", { id: toastId });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      runDispatch({ type: "error", error: message });
      toast.error(`Run failed: ${message}`, { id: toastId });
    }
  }, [payload]);

  const saveSetup = useCallback(() => {
    const ok = saveState<SavedState>({
      orbs: orbsState.orbs,
      profiles: profilesState.profiles,
      shareability_matrix: profilesState.shareabilityMatrix,
    });

    if (ok) toast.success("Saved your setup.");
    else toast.error("Could not save (localStorage error).");
  }, [orbsState.orbs, profilesState.profiles, profilesState.shareabilityMatrix]);

  const clearSavedSetup = useCallback(() => {
    clearState();
    toast("Cleared saved data.");
  }, []);

  const copySetupJson = useCallback(async () => {
    try {
      const serialized = JSON.stringify(
        {
          orbs: orbsState.orbs,
          profiles: profilesState.profiles,
          shareability_matrix: profilesState.shareabilityMatrix,
        },
        null,
        2
      );
      await navigator.clipboard.writeText(serialized);
      toast.success("Copied JSON to clipboard");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Clipboard unavailable";
      toast.error(`Copy failed: ${message}`);
    }
  }, [orbsState.orbs, profilesState.profiles, profilesState.shareabilityMatrix]);

  const setOrbs = useCallback((orbs: OrbIn[]) => {
    orbsDispatch({ type: "replace", orbs });
  }, []);

  const setShareabilityMatrix = useCallback((shareabilityMatrix: ShareabilityMatrix) => {
    profilesDispatch({ type: "set_shareability_matrix", shareabilityMatrix });
  }, []);

  const addProfile = useCallback(() => {
    profilesDispatch({ type: "add_profile" });
  }, []);

  const updateProfile = useCallback((index: number, profile: OptimizeProfileIn) => {
    profilesDispatch({ type: "update_profile", index, profile });
  }, []);

  const removeProfile = useCallback((index: number) => {
    profilesDispatch({ type: "remove_profile", index });
  }, []);

  const setProfileCategory = useCallback(
    (index: number, category: string, rarity: CategoryRarity | "") => {
      profilesDispatch({ type: "set_profile_category", index, category, rarity });
    },
    []
  );

  const value = useMemo<AppStateContextValue>(
    () => ({
      orbs: orbsState.orbs,
      profiles: profilesState.profiles,
      shareabilityMatrix: profilesState.shareabilityMatrix,
      loading: runState.loading,
      error: runState.error,
      result: runState.result,
      payload,
      setOrbs,
      setShareabilityMatrix,
      addProfile,
      updateProfile,
      removeProfile,
      setProfileCategory,
      runOptimize,
      saveSetup,
      clearSavedSetup,
      copySetupJson,
    }),
    [
      addProfile,
      orbsState.orbs,
      payload,
      profilesState.profiles,
      profilesState.shareabilityMatrix,
      removeProfile,
      runState.error,
      runState.loading,
      runState.result,
      setOrbs,
      setProfileCategory,
      setShareabilityMatrix,
      updateProfile,
      copySetupJson,
      clearSavedSetup,
      runOptimize,
      saveSetup,
    ]
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState(): AppStateContextValue {
  const context = useContext(AppStateContext);
  if (!context) {
    throw new Error("useAppState must be used within AppStateProvider");
  }
  return context;
}
