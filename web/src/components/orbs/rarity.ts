export const rarityBg: Record<string, string> = {
  Common: "bg-zinc-100 border-zinc-200",
  Magic: "bg-emerald-50 border-emerald-200",
  Rare: "bg-sky-50 border-sky-200",
  Epic: "bg-violet-50 border-violet-200",
  Legendary: "bg-amber-50 border-amber-200",
  Mythic: "bg-rose-50 border-rose-200",
};

export const rarityRing: Record<string, string> = {
  Common: "ring-zinc-200",
  Magic: "ring-emerald-200",
  Rare: "ring-sky-200",
  Epic: "ring-violet-200",
  Legendary: "ring-amber-200",
  Mythic: "ring-rose-200",
};

export function rarityClasses(rarity?: string) {
  const bg = rarityBg[rarity || ""] || "bg-zinc-50 border-zinc-200";
  const ring = rarityRing[rarity || ""] || "ring-zinc-200";
  return `${bg} ${ring}`;
}
