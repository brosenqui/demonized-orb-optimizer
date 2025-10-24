// Shared display constants/utilities for orb tiles & grids

import type { OrbIn, Rarity } from "../../lib/types";

// Emoji placeholders; swap for real SVGs later if you want.
export const TYPE_ICON: Record<string, string> = {
  Flame: "🔥",
  Water: "💧",
  Wind: "🍃",
  Earth: "🪨",
  Sun: "☀️",
  Grass: "🌿",
  Lightning: "⚡",
  Steel: "🛡️",
};

// Tailwind classes for rarity look
export const rarityCardClass: Record<string, string> = {
  Common: "bg-zinc-100 text-zinc-800 ring-zinc-300",
  Magic: "bg-green-100 text-green-900 ring-green-300",
  Rare: "bg-blue-100 text-blue-900 ring-blue-300",
  Epic: "bg-purple-100 text-purple-900 ring-purple-300",
  Legendary: "bg-amber-100 text-amber-900 ring-amber-300",
  Mythic: "bg-rose-100 text-rose-900 ring-rose-300",
};

export type Density = "comfortable" | "cozy" | "compact";

export function gridClassForDensity(d: Density): string {
  // Comfortable: 6/row, Cozy: 9/row, Compact: 12/row @ xl
  if (d === "compact")
    return "grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-12 2xl:grid-cols-12 gap-2";
  if (d === "cozy")
    return "grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-9 2xl:grid-cols-9 gap-3";
  return "grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-6 gap-4";
}

export function tileChromeForDensity(d: Density): string {
  return d === "compact" ? "rounded-xl ring-2 shadow-sm" : "rounded-2xl ring-2 shadow";
}

export function typeSizeForDensity(d: Density): string {
  return d === "compact" ? "text-xs" : d === "cozy" ? "text-sm" : "text-base";
}

export function iconSizeForDensity(d: Density): string {
  return d === "compact" ? "text-3xl" : d === "cozy" ? "text-4xl" : "text-5xl";
}

export function valueSizeForDensity(d: Density): string {
  return d === "compact" ? "text-[10px]" : d === "cozy" ? "text-xs" : "text-sm";
}

export const levelPillBase = "rounded-full font-semibold bg-black/70 text-white";
export function levelPillForDensity(d: Density): string {
  return d === "compact" ? `${levelPillBase} px-1.5 py-0.5 text-[10px]` : `${levelPillBase} px-2 py-0.5 text-xs`;
}

export const setBadgeBase = "inline-flex items-center rounded-md font-medium bg-white/85 border border-white/60 backdrop-blur";
export function setBadgeForDensity(d: Density): string {
  return d === "compact" ? `${setBadgeBase} px-1.5 py-0.5 text-[10px]` : `${setBadgeBase} px-2 py-0.5 text-xs`;
}

// In cozy/compact we hide extra details by default
export function showDetailsForDensity(d: Density) {
  const comfortable = d === "comfortable";
  return {
    showLevel: comfortable,
    showSet: comfortable,
    showValue: comfortable,
  };
}

// Simple clamp
export const clamp = (n: number, min = 0, max = Number.POSITIVE_INFINITY) => Math.max(min, Math.min(max, n));

// Normalize an incoming raw JSON orb to OrbIn
export function normalizeOrb(raw: any): OrbIn | null {
  const type = String(raw?.type ?? "").trim();
  const set = String(raw?.set ?? raw?.set ?? "").trim();
  const rarity = String(raw?.rarity ?? "Rare").trim();
  const valueNum = Number(raw?.value ?? 0);
  const levelNum = Number(raw?.level ?? 0);

  if (!type || !set) return null;

  const value = Number.isFinite(valueNum) ? Math.max(0, valueNum) : 0;
  let level = Number.isFinite(levelNum) ? levelNum : 0;
  level = clamp(level, 0, 9);

  return {
    type: type as OrbIn["type"],
    set: set as OrbIn["set"],
    rarity: rarity as OrbIn["rarity"],
    value,
    level,
  };
}
