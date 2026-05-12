import { parseOptimizeRequest, parseOptimizeResponse } from "./schemas";
import type { OptimizeRequest, OptimizeResponse } from "./types";

export const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export async function postOptimize(payload: OptimizeRequest): Promise<OptimizeResponse> {
  const validatedPayload = parseOptimizeRequest(payload);
  const res = await fetch(`${API_BASE}/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(validatedPayload),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }

  const json = (await res.json()) as unknown;
  return parseOptimizeResponse(json);
}
