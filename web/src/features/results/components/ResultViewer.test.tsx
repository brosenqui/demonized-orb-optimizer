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
    expect(screen.getByText("Advanced Diagnostics")).toBeInTheDocument();
    expect(screen.queryByText("Complete assignment")).not.toBeInTheDocument();
  });

  it("hides shared summary when no shared selections exist", () => {
    render(<ResultViewer data={NO_SHARED_SELECTIONS_RESPONSE} loading={false} error={null} />);
    expect(screen.queryByText("Shared Slot Summary")).not.toBeInTheDocument();
    expect(screen.getByText("Advanced Diagnostics")).toBeInTheDocument();
  });

  it("collapses and expands profile sections", () => {
    render(<ResultViewer data={SUCCESS_RESPONSE} loading={false} error={null} />);
    expect(screen.getByText("Soul")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Collapse profile Main" }));
    expect(screen.queryByText("Soul")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Expand profile Main" }));
    expect(screen.getByText("Soul")).toBeInTheDocument();
  });
});
