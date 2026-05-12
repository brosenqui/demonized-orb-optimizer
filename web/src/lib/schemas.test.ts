import { describe, expect, it } from "vitest";
import { parseOptimizeRequest, parseOptimizeResponse } from "@/lib/schemas";

describe("schemas", () => {
  it("parses and normalizes optimize request", () => {
    const request = parseOptimizeRequest({
      algorithm: "greedy",
      shareable_categories: ["Soul"],
      orbs: [
        {
          type: "Flame",
          set: "Lucifer",
          rarity: "Rare",
          value: "12.5",
          level: "3",
          awakened: "2",
        },
      ],
      profiles: [
        {
          name: "Main",
          weight: 1,
          objective: "sets-first",
          power: 2,
          epsilon: 0.02,
          set_priority: {},
          orb_weights: {},
          orb_level_weights: {},
          categories: { Soul: "Rare" },
        },
      ],
    });

    expect(request.orbs[0].value).toBe(12.5);
    expect(request.orbs[0].level).toBe(3);
    expect(request.orbs[0].awakened).toBe(2);
  });

  it("parses canonical optimize response", () => {
    const response = parseOptimizeResponse({
      ok: true,
      result: {
        summary: {
          combined_score: 12,
          requested_slots: 4,
          filled_slots: 3,
          is_partial: true,
          shared_summary: {
            requested_slots: 2,
            filled_slots: 1,
            is_partial: true,
            requested_positions: 2,
            filled_positions: 1,
            active_sets: { Lucifer: 1 },
            totals_by_type: { Flame: 12 },
            compromise_loss_total: 0.5,
            compromise_loss_by_profile: { Main: 0.5 },
            cap_limited_slots_by_profile: { Main: 1 },
            slots: [],
          },
          run_diagnostics: {
            algorithm: "greedy",
            duration_ms: 123,
            candidate_evaluations: 88,
          },
          profiles: [
            {
              name: "Main",
              score: 12,
              set_score: 8,
              orb_score: 4,
              requested_slots: 4,
              filled_slots: 3,
              is_partial: true,
            },
          ],
        },
        raw: {
          combined_score: 12,
          requested_slots: 4,
          filled_slots: 3,
          is_partial: true,
          shared_summary: {
            requested_slots: 2,
            filled_slots: 1,
            is_partial: true,
            requested_positions: 2,
            filled_positions: 1,
            active_sets: { Lucifer: 1 },
            totals_by_type: { Flame: 12 },
            compromise_loss_total: 0.5,
            compromise_loss_by_profile: { Main: 0.5 },
            cap_limited_slots_by_profile: { Main: 1 },
            slots: [],
          },
          run_diagnostics: {
            algorithm: "greedy",
            duration_ms: 123,
            candidate_evaluations: 88,
          },
          profiles: [
            {
              name: "Main",
              score: 12,
              set_score: 8,
              orb_score: 4,
              requested_slots: 4,
              filled_slots: 3,
              is_partial: true,
              assignments: {
                Soul: [
                  {
                    type: "Flame",
                    set: "Lucifer",
                    rarity: "Rare",
                    value: 12,
                    level: 2,
                    awakened: 1,
                  },
                ],
              },
            },
          ],
        },
      },
    });

    expect(response.ok).toBe(true);
    expect(response.result.raw.profiles[0].assignments.Soul).toHaveLength(1);
    expect(response.result.raw.shared_summary?.compromise_loss_total).toBe(0.5);
    expect(response.result.raw.run_diagnostics?.algorithm).toBe("greedy");
  });

  it("fails invalid response shapes", () => {
    expect(() => parseOptimizeResponse({ ok: true })).toThrow();
  });
});
