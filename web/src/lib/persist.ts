const KEY = "orbopt_state_v1"; // bump this if you change the shape

export type PersistedState<T = unknown> = T;

export function saveState<T>(obj: PersistedState<T>) {
  try {
    const json = JSON.stringify(obj);
    localStorage.setItem(KEY, json);
    return true;
  } catch (err) {
    console.error("Failed to save to localStorage:", err);
    return false;
  }
}

export function loadState<T = unknown>(): PersistedState<T> | null {
  try {
    const json = localStorage.getItem(KEY);
    if (!json) return null;
    return JSON.parse(json) as PersistedState<T>;
  } catch (err) {
    console.error("Failed to load from localStorage:", err);
    return null;
  }
}

export function clearState() {
  try {
    localStorage.removeItem(KEY);
  } catch (err) {
    console.error("Failed to clear localStorage:", err);
  }
}
