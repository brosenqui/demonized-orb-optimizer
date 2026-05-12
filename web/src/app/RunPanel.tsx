import Section from "@/components/ui/Section";
import { Button } from "@/components/ui/button";
import { useAppState } from "@/app/AppStateProvider";

export default function RunPanel() {
  const { loading, runOptimize, saveSetup, clearSavedSetup, copySetupJson } = useAppState();

  return (
    <Section title="Run">
      <p className="text-md text-zinc-600 mb-3">
        This web app runs the <span className="font-semibold">Greedy</span> optimizer.
      </p>
      <p className="text-sm text-zinc-600 mb-3">
        The Greedy Solver finds a strong orb setup fast by choosing the best option one step at a time.
        It looks at each slot, picks the orb that gives the biggest boost right now, then moves to the next.
        This approach does not test every possible combination, but it gets very close to the best result in a fraction of the time.
      </p>

      <div className="flex flex-wrap gap-2">
        <Button onClick={runOptimize} disabled={loading}>
          {loading ? "Running…" : "Run Optimizer"}
        </Button>
        <Button variant="secondary" onClick={saveSetup}>
          Save
        </Button>
        <Button variant="secondary" onClick={clearSavedSetup}>
          Clear Saved
        </Button>
        <Button variant="secondary" onClick={() => void copySetupJson()}>
          Copy Data JSON
        </Button>
      </div>
    </Section>
  );
}
