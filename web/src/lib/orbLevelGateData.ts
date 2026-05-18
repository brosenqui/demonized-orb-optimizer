export const ORB_LEVEL_GATES = [3, 6, 9] as const;

type OrbLevelGate = (typeof ORB_LEVEL_GATES)[number];

type GateValues = Record<OrbLevelGate, number>;

export const ORB_LEVEL_GATE_VALUES_BY_TYPE: Record<string, GateValues> = {
  Flame: { 3: 100, 6: 125, 9: 200 },
  Water: { 3: 2, 6: 2, 9: 3 },
  Wind: { 3: 15, 6: 15, 9: 15 },
  Earth: { 3: 30, 6: 40, 9: 50 },
  Sun: { 3: 3, 6: 4, 9: 5 },
  Grass: { 3: 25, 6: 50, 9: 100 },
  Lightning: { 3: 15, 6: 20, 9: 30 },
  Steel: { 3: 3, 6: 4, 9: 5 },
};

export const ORB_LEVEL_GATE_STAT_BY_TYPE: Record<string, string> = {
  Flame: "Normal ATK Amp %",
  Water: "Resurrection Chance %",
  Wind: "ASPD %",
  Earth: "HP %",
  Sun: "PVP Damage Reduction %",
  Grass: "Final DMG %",
  Lightning: "Boss ATK Damage %",
  Steel: "Effect Resistance %",
};

export function cumulativeLevelGateBonus(orbType: string, level: number): number {
  const gateValues = ORB_LEVEL_GATE_VALUES_BY_TYPE[orbType];
  if (!gateValues) return 0;
  const normalizedLevel = Number.isFinite(level) ? Math.max(0, level) : 0;
  return ORB_LEVEL_GATES.reduce(
    (sum, gate) => (normalizedLevel >= gate ? sum + (gateValues[gate] ?? 0) : sum),
    0
  );
}
