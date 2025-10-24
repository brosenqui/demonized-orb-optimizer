export const ORB_TYPES = [
  "Flame",
  "Water",
  "Wind",
  "Earth",
  "Sun",
  "Grass",
  "Lightning",
  "Steel",
] as const;

export type OrbType = typeof ORB_TYPES[number];

export const ORB_SETS = [
  "Lucifer",
  "Mammon",
  "Leviathan",
  "Satan",
  "Asmodeus",
  "Beelzebub",
  "Belphegor",
] as const;

export type OrbSet = typeof ORB_SETS[number];
