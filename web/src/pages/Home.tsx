import React, { useEffect, useMemo, useState } from "react";
import OrbsEditor from "../components/orbs/OrbsEditor";
import ProfilesEditor from "../components/profiles/ProfilesEditor";
import ResultViewer from "../components/results/ResultViewer";
import Section from "../components/ui/Section";
import { postOptimize } from "../lib/api";
import type {
  OptimizeRequest,
  OptimizeResponse,
  OptimizeProfileIn,
  OrbIn,
} from "../lib/types";
import { saveState, loadState, clearState } from "../lib/persist";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { ORB_SETS, ORB_TYPES } from "../lib/orbData";

type SavedState = {
  orbs: OrbIn[];
  profiles: OptimizeProfileIn[];
  shareable: string[];
};

export default function Home() {
  const [orbs, setOrbs] = useState<OrbIn[]>([]);
  const [profiles, setProfiles] = useState<OptimizeProfileIn[]>([]);
  const [shareable, setShareable] = useState<string[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resp, setResp] = useState<OptimizeResponse | null>(null);

  // Load saved state on mount
  useEffect(() => {
    const saved = loadState<SavedState>();
    if (saved) {
      setOrbs(saved.orbs ?? []);
      setProfiles(saved.profiles ?? []);
      setShareable(saved.shareable ?? []);
      toast.success("Restored your saved setup.");
    }
  }, []);

  // Greedy-only payload
  const payload: OptimizeRequest = useMemo(
    () => ({
      orbs,
      profiles,
      shareable_categories: shareable,
      algorithm: "greedy",
    }),
    [orbs, profiles, shareable]
  );

  async function handleRun() {
    setLoading(true);
    setError(null);
    setResp(null);
    const t = toast.loading("Running optimizer…");
    try {
      const data = await postOptimize(payload);
      setResp(data);
      toast.success("Optimization complete.", { id: t });
    } catch (e: any) {
      const msg = e?.message || String(e);
      setError(msg);
      toast.error(`Run failed: ${msg}`, { id: t });
    } finally {
      setLoading(false);
    }
  }

  function handleSave() {
    const ok = saveState<SavedState>({ orbs, profiles, shareable });
    if (ok) toast.success("Saved your setup.");
    else toast.error("Could not save (localStorage error).");
  }

  function handleClearSaved() {
    clearState();
    toast("Cleared saved data.");
  }

  return (
    <div className="max-w-6xl mx-auto px-5 pb-10 space-y-6">

      <OrbsEditor orbs={orbs} setOrbs={setOrbs} />
      <ProfilesEditor
        profiles={profiles}
        setProfiles={setProfiles}
        shareable={shareable}
        setShareable={setShareable}
        availableSets={ORB_SETS}
        availableTypes={ORB_TYPES}
      />

      <Section title="Run">
        <p className="text-md text-zinc-600 mb-3">
          This web app runs the <span className="font-semibold">Greedy</span> optimizer.<br />
        </p>
        <p className="text-sm text-zinc-600 mb-3">
          The Greedy Solver finds a strong orb setup fast by choosing the best option one step at a time.<br />
          It looks at each slot, picks the orb that gives the biggest boost right now, then moves to the next.<br />
          This approach doesn't test every possible combination, but it gets very close to the best result - in a fraction of the time.<br />
          Use it when you want great results quickly, without waiting for a full exhaustive search.<br />
          </p>
        <div className="flex flex-wrap gap-2">
          <Button className="btn btn-primary" onClick={handleRun} disabled={loading}>
            {loading ? "Running…" : "Run Optimizer"}
          </Button>
          <Button variant="secondary" onClick={handleSave}>
            Save
          </Button>
          <Button variant="secondary" onClick={handleClearSaved}>
            Clear Saved
          </Button>
          <Button
            variant="secondary"
            onClick={() =>
              navigator.clipboard.writeText(
                JSON.stringify({ orbs, profiles, shareable }, null, 2)
              ).then(() => toast.success("Copied JSON to clipboard"))
            }
          >
            Copy Data JSON
          </Button>
        </div>
      </Section>

      <ResultViewer data={resp} loading={loading} error={error} />
    </div>
  );
}
