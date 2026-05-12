import { describe, expect, it } from "vitest";
import { normalizeOrb, parseImportedOrbs, sanitizeOrbInput } from "@/features/orbs/utils/orbInput";

describe("orbInput utilities", () => {
  it("normalizes imported orb values and clamps awakened/level", () => {
    const normalized = normalizeOrb({
      type: "Flame",
      set: "Lucifer",
      rarity: "Rare",
      value: "12.5",
      level: 42,
      awakened: 3.7,
    });

    expect(normalized).toEqual({
      type: "Flame",
      set: "Lucifer",
      rarity: "Rare",
      value: 12.5,
      level: 9,
      awakened: 3,
      slot_index: undefined,
    });
  });

  it("falls back unknown rarity to Rare", () => {
    const normalized = normalizeOrb({
      type: "Water",
      set: "Mammon",
      rarity: "Unknown",
      value: 0,
      level: 0,
      awakened: 0,
    });

    expect(normalized?.rarity).toBe("Rare");
  });

  it("parses valid orb arrays and strips invalid entries", () => {
    const parsed = parseImportedOrbs(
      JSON.stringify([
        { type: "Flame", set: "Lucifer", rarity: "Rare", value: 5, level: 1, awakened: 2 },
        { type: "", set: "Mammon", rarity: "Rare", value: 1, level: 1, awakened: 0 },
      ])
    );

    expect(parsed).toHaveLength(1);
    expect(parsed[0].type).toBe("Flame");
  });

  it("throws when JSON does not contain orbs", () => {
    expect(() => parseImportedOrbs(JSON.stringify({ foo: [] }))).toThrow(
      "JSON must be an array of orbs"
    );
  });

  it("sanitizes direct Orb input payload", () => {
    const sanitized = sanitizeOrbInput({
      type: "Steel",
      set: "Satan",
      rarity: "Legendary",
      value: -5,
      level: -2,
      awakened: -9,
    });

    expect(sanitized.value).toBe(0);
    expect(sanitized.level).toBe(0);
    expect(sanitized.awakened).toBe(0);
  });
});
