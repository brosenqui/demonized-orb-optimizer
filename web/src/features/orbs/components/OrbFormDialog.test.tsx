import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useState } from "react";
import OrbFormDialog, { type OrbFormState } from "@/features/orbs/components/OrbFormDialog";

function TestHarness({ onSave }: { onSave: () => void }) {
  const [form, setForm] = useState<OrbFormState>({
    type: "Flame",
    set: "Lucifer",
    rarity: "Rare",
    value: 0,
    level: 0,
    awakened: 0,
  });

  return (
    <>
      <OrbFormDialog
        open
        onOpenChange={() => undefined}
        isEditing={false}
        form={form}
        setForm={setForm}
        onSave={onSave}
      />
      <div data-testid="form-json">{JSON.stringify(form)}</div>
    </>
  );
}

describe("OrbFormDialog", () => {
  it("clamps level and awakened values during editing", () => {
    const onSave = vi.fn();
    render(<TestHarness onSave={onSave} />);

    fireEvent.change(screen.getByLabelText("Level"), { target: { value: "999" } });
    fireEvent.change(screen.getByLabelText("Awakened Levels"), { target: { value: "-3.8" } });

    const parsed = JSON.parse(screen.getByTestId("form-json").textContent || "{}");
    expect(parsed.level).toBe(9);
    expect(parsed.awakened).toBe(0);

    fireEvent.click(screen.getByRole("button", { name: "Add" }));
    expect(onSave).toHaveBeenCalledTimes(1);
  });
});
