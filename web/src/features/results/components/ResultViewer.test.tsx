import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultViewer from "@/features/results/components/ResultViewer";
import type { OptimizeResponse } from "@/lib/types";

const SUCCESS_RESPONSE: OptimizeResponse = {
  ok: true,
  result: {
    summary: {
      combined_score: 10,
      is_partial: true,
      shared_summary: {
        active_sets: { Lucifer: 1 },
        totals_by_type: { Flame: 10 },
        compromise_loss_total: 0,
        compromise_loss_by_profile: { Main: 0 },
        cap_limited_slots_by_profile: {},
        slots: [],
      },
      run_diagnostics: {
        algorithm: "greedy",
        duration_ms: 12,
        candidate_evaluations: 4,
      },
      profiles: [
        {
          name: "Main",
          score: 10,
          set_score: 6,
          orb_score: 4,
          is_partial: true,
        },
      ],
    },
    raw: {
      combined_score: 10,
      is_partial: true,
      shared_summary: {
        active_sets: { Lucifer: 1 },
        totals_by_type: { Flame: 10 },
        compromise_loss_total: 0,
        compromise_loss_by_profile: { Main: 0 },
        cap_limited_slots_by_profile: {},
        slots: [],
      },
      run_diagnostics: {
        algorithm: "greedy",
        duration_ms: 12,
        candidate_evaluations: 4,
      },
      profiles: [
        {
          name: "Main",
          score: 10,
          set_score: 6,
          orb_score: 4,
          is_partial: true,
          assignments: {
            Soul: [
              {
                type: "Flame",
                set: "Lucifer",
                rarity: "Rare",
                value: 10,
                level: 2,
                awakened: 1,
              },
            ],
          },
        },
      ],
    },
  },
};

const NO_SHARED_SELECTIONS_RESPONSE: OptimizeResponse = {
  ...SUCCESS_RESPONSE,
  result: {
    ...SUCCESS_RESPONSE.result,
    summary: {
      ...SUCCESS_RESPONSE.result.summary,
      shared_summary: {
        active_sets: {},
        totals_by_type: {},
        compromise_loss_total: 0,
        compromise_loss_by_profile: {},
        cap_limited_slots_by_profile: {},
        slots: [],
      },
    },
    raw: {
      ...SUCCESS_RESPONSE.result.raw,
      shared_summary: {
        active_sets: {},
        totals_by_type: {},
        compromise_loss_total: 0,
        compromise_loss_by_profile: {},
        cap_limited_slots_by_profile: {},
        slots: [],
      },
    },
  },
};

const TWO_PROFILE_RESPONSE: OptimizeResponse = {
  ...SUCCESS_RESPONSE,
  result: {
    ...SUCCESS_RESPONSE.result,
    summary: {
      ...SUCCESS_RESPONSE.result.summary,
      shared_summary: {
        active_sets: { Lucifer: 1 },
        totals_by_type: { Flame: 10 },
        compromise_loss_total: 0,
        compromise_loss_by_profile: { Main: 0, Alt: 0 },
        cap_limited_slots_by_profile: {},
        slots: [
          {
            category: "Soul",
            slot_index: 0,
            profiles: ["Main", "Alt"],
            is_uniform: true,
            orb: {
              type: "Flame",
              set: "Lucifer",
              rarity: "Rare",
              value: 10,
              level: 2,
              awakened: 1,
            },
            profile_orbs: {
              Main: {
                type: "Flame",
                set: "Lucifer",
                rarity: "Rare",
                value: 10,
                level: 2,
                awakened: 1,
              },
              Alt: {
                type: "Flame",
                set: "Lucifer",
                rarity: "Rare",
                value: 10,
                level: 2,
                awakened: 1,
              },
            },
            profile_impacts: [
              {
                profile: "Main",
                selected_score: 1,
                solo_best_score: 1,
                compromise_loss: 0,
                selected_d_set: 0.5,
                selected_d_orb: 0.5,
                solo_best_d_set: 0.5,
                solo_best_d_orb: 0.5,
                cap_limited: false,
              },
              {
                profile: "Alt",
                selected_score: 1,
                solo_best_score: 1,
                compromise_loss: 0,
                selected_d_set: 0.5,
                selected_d_orb: 0.5,
                solo_best_d_set: 0.5,
                solo_best_d_orb: 0.5,
                cap_limited: false,
              },
            ],
          },
        ],
      },
      profiles: [
        {
          name: "Main",
          score: 10,
          set_score: 6,
          orb_score: 4,
          is_partial: true,
        },
        {
          name: "Alt",
          score: 8,
          set_score: 5,
          orb_score: 3,
          is_partial: false,
        },
      ],
    },
    raw: {
      ...SUCCESS_RESPONSE.result.raw,
      shared_summary: {
        active_sets: { Lucifer: 1 },
        totals_by_type: { Flame: 10 },
        compromise_loss_total: 0,
        compromise_loss_by_profile: { Main: 0, Alt: 0 },
        cap_limited_slots_by_profile: {},
        slots: [
          {
            category: "Soul",
            slot_index: 0,
            profiles: ["Main", "Alt"],
            is_uniform: true,
            orb: {
              type: "Flame",
              set: "Lucifer",
              rarity: "Rare",
              value: 10,
              level: 2,
              awakened: 1,
            },
            profile_orbs: {
              Main: {
                type: "Flame",
                set: "Lucifer",
                rarity: "Rare",
                value: 10,
                level: 2,
                awakened: 1,
              },
              Alt: {
                type: "Flame",
                set: "Lucifer",
                rarity: "Rare",
                value: 10,
                level: 2,
                awakened: 1,
              },
            },
            profile_impacts: [
              {
                profile: "Main",
                selected_score: 1,
                solo_best_score: 1,
                compromise_loss: 0,
                selected_d_set: 0.5,
                selected_d_orb: 0.5,
                solo_best_d_set: 0.5,
                solo_best_d_orb: 0.5,
                cap_limited: false,
              },
              {
                profile: "Alt",
                selected_score: 1,
                solo_best_score: 1,
                compromise_loss: 0,
                selected_d_set: 0.5,
                selected_d_orb: 0.5,
                solo_best_d_set: 0.5,
                solo_best_d_orb: 0.5,
                cap_limited: false,
              },
            ],
          },
        ],
      },
      profiles: [
        {
          name: "Main",
          score: 10,
          set_score: 6,
          orb_score: 4,
          is_partial: true,
          assignments: {
            Soul: [
              {
                type: "Flame",
                set: "Lucifer",
                rarity: "Rare",
                value: 10,
                level: 2,
                awakened: 1,
              },
            ],
          },
        },
        {
          name: "Alt",
          score: 8,
          set_score: 5,
          orb_score: 3,
          is_partial: false,
          assignments: {
            Wings: [
              {
                type: "Wind",
                set: "Belphegor",
                rarity: "Epic",
                value: 7,
                level: 3,
                awakened: 0,
              },
            ],
          },
        },
      ],
    },
  },
};

describe("ResultViewer", () => {
  it("renders loading state", () => {
    render(<ResultViewer data={null} loading error={null} />);
    expect(screen.getByText("Running optimization…")).toBeInTheDocument();
  });

  it("renders error state", () => {
    render(<ResultViewer data={null} loading={false} error="boom" />);
    expect(screen.getByText("boom")).toBeInTheDocument();
  });

  it("renders empty state", () => {
    render(<ResultViewer data={null} loading={false} error={null} />);
    expect(screen.getByText("No results yet.")).toBeInTheDocument();
  });

  it("renders success payload", () => {
    render(<ResultViewer data={SUCCESS_RESPONSE} loading={false} error={null} />);
    expect(screen.getByText("Profile: Main")).toBeInTheDocument();
    expect(screen.getByText("Combined Score:")).toBeInTheDocument();
    expect(screen.getByText("Stat Breakdown (Shared + Profile-only)")).toBeInTheDocument();
    expect(screen.getByText("Active Sets (Shared + Profile-only)")).toBeInTheDocument();
    expect(screen.getByText("Totals by Type (Shared + Profile-only)")).toBeInTheDocument();
    expect(screen.getByText("Orb Level Stats (Shared + Profile-only)")).toBeInTheDocument();
    expect(screen.getByText("Advanced Diagnostics")).toBeInTheDocument();
    expect(screen.queryByText("Complete assignment")).not.toBeInTheDocument();
  });

  it("shows shared-specific breakdown even when no shared selections exist", () => {
    render(<ResultViewer data={NO_SHARED_SELECTIONS_RESPONSE} loading={false} error={null} />);
    expect(screen.getByText("Stat Breakdown (Shared + Profile-only)")).toBeInTheDocument();
    expect(screen.getByText("Shared Slots:")).toBeInTheDocument();
    expect(screen.getByText("Advanced Diagnostics")).toBeInTheDocument();
  });

  it("switches profiles using tabs", () => {
    render(<ResultViewer data={TWO_PROFILE_RESPONSE} loading={false} error={null} />);
    expect(screen.getByText("Stat Breakdown (Shared + Profile-only)")).toBeInTheDocument();
    expect(screen.getByText("Shared With:")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Main" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Soul")).toBeInTheDocument();
    expect(screen.queryByText("Wings")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Alt" }));
    expect(screen.getByRole("tab", { name: "Alt" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Wings")).toBeInTheDocument();
    expect(screen.queryByText("Soul")).not.toBeInTheDocument();
    expect(screen.queryByText("Shared With:")).not.toBeInTheDocument();
  });
});
