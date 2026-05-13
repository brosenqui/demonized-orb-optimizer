import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useState } from "react";
import OrbsEditor from "@/features/orbs/components/OrbsEditor";
import type { OrbIn } from "@/lib/types";

const INITIAL_ORBS: OrbIn[] = [
  { type: "Flame", set: "Lucifer", rarity: "Rare", value: 1, level: 1, awakened: 0 },
];

function TestHarness() {
  const [orbs, setOrbs] = useState<OrbIn[]>(INITIAL_ORBS);
  return (
    <>
      <OrbsEditor orbs={orbs} setOrbs={setOrbs} />
      <div data-testid="orb-count">{orbs.length}</div>
    </>
  );
}

describe("OrbsEditor import flow", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows error for invalid json and imports valid payload", () => {
    render(<TestHarness />);

    fireEvent.click(screen.getByRole("button", { name: "Import JSON" }));

    const textarea = screen.getByPlaceholderText(/\[/);
    fireEvent.change(textarea, { target: { value: "{" } });
    fireEvent.click(screen.getByRole("button", { name: "Import" }));

    expect(screen.getByText(/Expected|Unexpected|Invalid/i)).toBeInTheDocument();

    fireEvent.change(textarea, {
      target: {
        value: JSON.stringify([
          { type: "Water", set: "Mammon", rarity: "Epic", value: 2, level: 2, awakened: 1 },
          { type: "Steel", set: "Satan", rarity: "Magic", value: 3, level: 3, awakened: 0 },
        ]),
      },
    });
    fireEvent.click(screen.getByRole("button", { name: "Import" }));

    expect(screen.getByTestId("orb-count").textContent).toBe("2");
  });

  it("confirms before clearing all orbs", () => {
    const confirmSpy = vi.spyOn(window, "confirm");
    render(<TestHarness />);

    confirmSpy.mockReturnValueOnce(false);
    fireEvent.click(screen.getByRole("button", { name: "Clear all orbs" }));
    expect(screen.getByTestId("orb-count").textContent).toBe("1");

    confirmSpy.mockReturnValueOnce(true);
    fireEvent.click(screen.getByRole("button", { name: "Clear all orbs" }));
    expect(screen.getByTestId("orb-count").textContent).toBe("0");
  });

  it("opens add-orb dialog with Alt+A shortcut", () => {
    render(<TestHarness />);

    fireEvent.keyDown(window, { key: "a", altKey: true });

    expect(screen.getByRole("heading", { name: "Add Orb" })).toBeInTheDocument();
  });

  it("focuses search input on slash shortcut", async () => {
    render(<TestHarness />);

    fireEvent.keyDown(window, { key: "/" });

    await waitFor(() => expect(screen.getByLabelText("Search")).toHaveFocus());
  });

  it("starts with filters collapsed by default", () => {
    render(<TestHarness />);
    expect(screen.queryByLabelText("Search")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Expand filters" }));
    expect(screen.getByLabelText("Search")).toBeInTheDocument();
  });

  it("collapses and expands orb collection", () => {
    render(<TestHarness />);

    expect(screen.getByText("Filters")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Collapse orb collection" }));
    expect(screen.queryByText("Filters")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Expand orb collection" }));
    expect(screen.getByText("Filters")).toBeInTheDocument();
  });
});
