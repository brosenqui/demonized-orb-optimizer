import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultViewer from "@/features/results/components/ResultViewer";
import type { OptimizeResponse } from "@/lib/types";

const SUCCESS_RESPONSE: OptimizeResponse = {
  ok: true,
  result: {
    summary: {
      combined_score: 10,
      requested_slots: 4,
      filled_slots: 3,
      is_partial: true,
      shared_summary: {
        requested_slots: 1,
        filled_slots: 1,
        is_partial: false,
        requested_positions: 1,
        filled_positions: 1,
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
          requested_slots: 4,
          filled_slots: 3,
          is_partial: true,
        },
      ],
    },
    raw: {
      combined_score: 10,
      requested_slots: 4,
      filled_slots: 3,
      is_partial: true,
      shared_summary: {
        requested_slots: 1,
        filled_slots: 1,
        is_partial: false,
        requested_positions: 1,
        filled_positions: 1,
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
          requested_slots: 4,
          filled_slots: 3,
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
    expect(screen.getByText("Shared Slot Summary")).toBeInTheDocument();
    expect(screen.getByText("Advanced shared diagnostics")).toBeInTheDocument();
  });
});
