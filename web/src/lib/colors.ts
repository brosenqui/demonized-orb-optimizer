export type Rarity =
  | "Common"
  | "Magic"
  | "Rare"
  | "Epic"
  | "Legendary"
  | "Mythic";

export const rarityToSlots: Record<Rarity, number> = {
  Common: 0,              // not used for categories, but safe
  Magic: 0,
  Rare: 1,
  Epic: 2,
  Legendary: 3,
  Mythic: 4,
};

export const rarityBgClass: Record<Rarity, string> = {
  Common: "bg-zinc-100 text-zinc-800",
  Magic: "bg-green-100 text-green-900",
  Rare: "bg-blue-100 text-blue-900",
  Epic: "bg-purple-100 text-purple-900",
  Legendary: "bg-amber-100 text-amber-900",
  Mythic: "bg-rose-100 text-rose-900",
};

export const rarityRingClass: Record<Rarity, string> = {
  Common: "ring-zinc-300",
  Magic: "ring-green-300",
  Rare: "ring-blue-300",
  Epic: "ring-purple-300",
  Legendary: "ring-amber-300",
  Mythic: "ring-rose-300",
};
