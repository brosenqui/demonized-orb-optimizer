import type { OptimizeRequest, OptimizeResponse } from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE_URL || ""; // same-origin

export async function postOptimize(payload: OptimizeRequest): Promise<OptimizeResponse> {
  const res = await fetch(`${API_BASE}/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`HTTP ${res.status}: ${txt}`);
  }
  return res.json();
}
