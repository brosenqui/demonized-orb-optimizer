import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ShareabilityMatrixEditor from "@/features/profiles/components/ShareabilityMatrixEditor";
import type { OptimizeProfileIn, ShareabilityMatrix } from "@/lib/types";

const PROFILES: OptimizeProfileIn[] = [
  {
    name: "A",
    weight: 1,
    objective: "sets-first",
    power: 1,
    epsilon: 0.01,
    set_priority: {},
    orb_weights: {},
    orb_level_weights: {},
    categories: { Soul: "Rare" },
  },
  {
    name: "B",
    weight: 1,
    objective: "sets-first",
    power: 1,
    epsilon: 0.01,
    set_priority: {},
    orb_weights: {},
    orb_level_weights: {},
    categories: { Soul: "Rare" },
  },
];

describe("ShareabilityMatrixEditor", () => {
  it("updates cell values and supports row actions", () => {
    const onChange = vi.fn();
    const matrix: ShareabilityMatrix = {
      Soul: { A: false, B: false },
    };

    render(<ShareabilityMatrixEditor profiles={PROFILES} value={matrix} onChange={onChange} />);

    expect(
      screen.getByText(
        "Checked profiles are strictly linked per slot for that category and must receive the same orb."
      )
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("checkbox", {
        name: "Require shared orb for Soul category on A",
      })
    );
    expect(onChange).toHaveBeenCalled();

    fireEvent.click(
      screen.getByRole("button", {
        name: "Enable sharing for all profiles on Soul",
      })
    );
    const latest = onChange.mock.calls[onChange.mock.calls.length - 1][0] as ShareabilityMatrix;
    expect(latest.Soul.A).toBe(true);
    expect(latest.Soul.B).toBe(true);
  });
});
