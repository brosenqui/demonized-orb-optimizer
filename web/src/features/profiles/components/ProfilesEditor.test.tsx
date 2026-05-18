import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ProfilesEditor from "@/features/profiles/components/ProfilesEditor";
import type { OptimizeProfileIn, ShareabilityMatrix } from "@/lib/types";

const PROFILE: OptimizeProfileIn = {
  name: "Main",
  weight: 1,
  objective: "sets-first",
  power: 2,
  epsilon: 0.02,
  set_priority: {},
  orb_weights: {},
  orb_level_weights: {},
  categories: {
    Soul: "Legendary",
  },
};

describe("ProfilesEditor", () => {
  const MATRIX: ShareabilityMatrix = {
    Soul: { Main: true },
  };

  it("collapses and expands profile configuration cards", () => {
    render(
      <ProfilesEditor
        profiles={[PROFILE]}
        shareabilityMatrix={MATRIX}
        setShareabilityMatrix={vi.fn()}
        onAddProfile={vi.fn()}
        onUpdateProfile={vi.fn()}
        onRemoveProfile={vi.fn()}
        onSetCategory={vi.fn()}
        availableSets={["Leviathan"]}
        availableTypes={["Flame"]}
      />
    );

    expect(screen.getByLabelText("Profile name")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Collapse profile Main" }));
    expect(screen.queryByLabelText("Profile name")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Expand profile Main" }));
    expect(screen.getByLabelText("Profile name")).toBeInTheDocument();
  });
});
