import { useState } from "react";
import Section from "@/components/ui/Section";
import { HelpTooltip } from "@/components/ui/helpToolTip";
import GateStatComparisonTable from "@/features/results/components/GateStatComparisonTable";
import LoadoutStatTables from "@/features/results/components/LoadoutStatTables";
import ProfileResults from "@/features/results/components/ProfileResults";
import { sharedStatsForProfile } from "@/features/results/utils/resultStats";
import { parseResultsFromRaw } from "@/lib/resultParser";
import type { OptimizeResponse, OptimizeSummaryProfile } from "@/lib/types";

function rounded(value: number | null | undefined): string | null {
  if (value == null || !Number.isFinite(value)) return null;
  return Number(value.toFixed(6)).toString();
}

function SummaryChip({ label, value }: { label: string; value: number | null | undefined }) {
  const display = rounded(value);
  if (display === null) return null;
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-zinc-200 bg-zinc-100 px-2 py-1 text-xs">
      <span className="text-zinc-600">{label}:</span>
      <span className="font-mono">{display}</span>
    </span>
  );
}

function resolveSummaryProfiles(data: OptimizeResponse): OptimizeSummaryProfile[] {
  return data.result.summary.profiles;
}

function summaryByName(
  summaryProfiles: readonly OptimizeSummaryProfile[]
): Record<string, OptimizeSummaryProfile> {
  return Object.fromEntries(summaryProfiles.map((profile) => [profile.name, profile]));
}

function titleCase(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function formatDiagnosticValue(value: unknown): string {
  if (value == null) return "—";
  if (Array.isArray(value)) return value.map((item) => String(item)).join(", ");
  if (typeof value === "number") return rounded(value) ?? "0";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function diagnosticTooltip(key: string): string {
  const map: Record<string, string> = {
    algorithm:
      "Which solver generated this run (for example greedy or beam), useful when comparing behavior across methods.",
    duration_ms:
      "End-to-end solver runtime in milliseconds. Use this to compare latency across solver settings and inputs.",
    time_budget_ms:
      "Configured runtime budget for this run in milliseconds. The solver tries to stop near this limit.",
    time_budget_hit:
      "Whether the solver hit its time budget and stopped early. If true, results may be lower quality than unconstrained runs.",
    starts_planned:
      "How many greedy starts were intended (deterministic orders plus randomized restarts). More starts can improve quality but cost time.",
    starts_executed:
      "How many greedy starts actually ran before completion or timeout. If lower than planned, the time budget likely constrained search.",
    beam_width:
      "Maximum number of beam states retained per step. Higher values usually improve search quality but increase runtime.",
    topk_per_type:
      "Greedy candidate limit per orb type. Higher values widen search options but add scoring work.",
    topk_per_category:
      "Beam candidate limit per category before expansion. Higher values increase coverage but can raise compute cost.",
    parallelism_config:
      "Requested parallel execution mode for beam scoring (auto/process/thread/serial).",
    parallelism_used:
      "Actual execution mode(s) used during the run after fallbacks. Helps explain runtime differences across environments.",
    categories_total:
      "Total categories in scope for this optimization run.",
    categories_processed:
      "How many categories were fully processed before the solver ended. If less than total, the run likely ended early.",
    candidate_evaluations:
      "Count of scored candidates/combos. Higher counts indicate broader search but more compute.",
    set_cap_rejections:
      "Candidates rejected due to set-piece cap violations. High values indicate caps are heavily constraining the search.",
    no_viable_slots:
      "Slots where no legal candidate could be assigned under current constraints. This is a direct driver of partial outcomes.",
    expansion_attempts:
      "Beam expansion attempts considered before pruning/feasibility filtering.",
    valid_expansions:
      "Beam expansions that passed constraints and remained in the candidate pool.",
    no_feasible_categories:
      "Categories where even full retry produced no feasible continuation. Indicates hard constraint bottlenecks.",
    shareable_slots_attempted:
      "Number of shared-slot positions the greedy run attempted to fill.",
    shareable_slots_filled:
      "Number of shared-slot positions successfully filled. Compare against attempted to gauge shared-slot constraint pressure.",
    nonshareable_slots_attempted:
      "Number of non-shared slot positions the greedy run attempted to fill.",
    nonshareable_slots_filled:
      "Number of non-shared slot positions successfully filled. Gaps indicate inventory or constraint bottlenecks.",
    restarts_configured:
      "Configured number of randomized greedy restarts. More restarts can improve best-found quality at higher runtime cost.",
    seed:
      "Random seed used for restart shuffling, included for reproducibility when comparing runs.",
    best_start_score:
      "Best per-start score seen during the run. Useful for estimating upside achieved by multi-start search.",
    worst_start_score:
      "Worst per-start score seen during the run. The spread vs best_start_score indicates sensitivity to start order.",
  };
  return (
    map[key] ??
    "Additional run telemetry metric reported by the solver for debugging and tuning search quality vs runtime."
  );
}

function orderedDiagnostics(diagnostics: Record<string, unknown>): Array<[string, unknown]> {
  const preferred = [
    "algorithm",
    "duration_ms",
    "time_budget_ms",
    "time_budget_hit",
    "starts_planned",
    "starts_executed",
    "beam_width",
    "topk_per_type",
    "topk_per_category",
    "parallelism_config",
    "parallelism_used",
    "categories_total",
    "categories_processed",
    "candidate_evaluations",
    "set_cap_rejections",
    "no_viable_slots",
    "expansion_attempts",
    "valid_expansions",
    "no_feasible_categories",
  ];
  const entries = Object.entries(diagnostics);
  const index = new Map(preferred.map((key, idx) => [key, idx]));
  return entries.sort((left, right) => {
    const leftIdx = index.get(left[0]) ?? Number.MAX_SAFE_INTEGER;
    const rightIdx = index.get(right[0]) ?? Number.MAX_SAFE_INTEGER;
    return leftIdx - rightIdx || left[0].localeCompare(right[0]);
  });
}

type ResultViewerProps = {
  data: OptimizeResponse | null;
  loading: boolean;
  error: string | null;
};

export default function ResultViewer({ data, loading, error }: ResultViewerProps) {
  const [selectedProfileIndex, setSelectedProfileIndex] = useState(0);

  if (loading) {
    return (
      <Section title="Results">
        <p>Running optimization…</p>
      </Section>
    );
  }

  if (error) {
    return (
      <Section title="Results">
        <p className="text-red-600">{error}</p>
      </Section>
    );
  }

  if (!data) {
    return (
      <Section title="Results">
        <p className="text-sm text-zinc-500">No results yet.</p>
      </Section>
    );
  }

  const parsed = parseResultsFromRaw(data.result.raw);
  if (!parsed || parsed.profiles.length === 0) {
    return (
      <Section title="Results">
        <p className="text-sm text-zinc-500">No profile assignments returned.</p>
      </Section>
    );
  }

  const summaryProfiles = resolveSummaryProfiles(data);
  const summaries = summaryByName(summaryProfiles);
  const runDiagnostics = parsed.run_diagnostics && Object.keys(parsed.run_diagnostics).length > 0
    ? parsed.run_diagnostics
    : null;
  const hasSharedSummary = (parsed.shared_summary?.slots.length ?? 0) > 0;
  const safeSelectedProfileIndex =
    selectedProfileIndex >= 0 && selectedProfileIndex < parsed.profiles.length
      ? selectedProfileIndex
      : 0;
  const selectedProfile = parsed.profiles[safeSelectedProfileIndex];
  const selectedSummary = summaries[selectedProfile.name];
  const selectedSharedStats = sharedStatsForProfile(
    selectedProfile.assignments,
    parsed.shared_summary,
    selectedProfile.name
  );
  const hasSelectedSharedSlots = selectedSharedStats.shared_slot_count > 0;
  const selectedProfilePanelId = `result-profile-panel-${safeSelectedProfileIndex}`;

  return (
    <Section title="Results">
      {parsed.combined_score != null && (
        <div className="mb-3 text-sm text-zinc-600">
          Combined Score: <span className="font-mono">{rounded(parsed.combined_score)}</span>
        </div>
      )}
      <div className="space-y-4">
        <div
          className="flex flex-wrap gap-2"
          role="tablist"
          aria-label="Result profiles"
        >
          {parsed.profiles.map((profile, index) => {
            const isActive = index === safeSelectedProfileIndex;
            return (
              <button
                key={`${profile.name}-${index}`}
                role="tab"
                id={`result-profile-tab-${index}`}
                aria-selected={isActive}
                aria-controls={`result-profile-panel-${index}`}
                tabIndex={isActive ? 0 : -1}
                type="button"
                onClick={() => setSelectedProfileIndex(index)}
                className={[
                  "rounded-full border px-3 py-1.5 text-sm transition",
                  isActive
                    ? "border-zinc-800 bg-zinc-800 text-white"
                    : "border-zinc-200 bg-white text-zinc-700 hover:bg-zinc-100",
                ].join(" ")}
              >
                {profile.name}
              </button>
            );
          })}
        </div>

        <div
          role="tabpanel"
          id={selectedProfilePanelId}
          aria-labelledby={`result-profile-tab-${safeSelectedProfileIndex}`}
          className="rounded-2xl border border-zinc-200 bg-white/70 p-4 shadow-sm backdrop-blur"
        >
          <div className="mb-3 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold">Profile: {selectedProfile.name}</h3>
              {selectedProfile.is_partial && (
                <span className="text-xs text-zinc-500">Partial assignment</span>
              )}
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              <SummaryChip label="Total" value={selectedSummary?.score ?? selectedProfile.score} />
              <SummaryChip label="Sets" value={selectedSummary?.set_score ?? selectedProfile.set_score} />
              <SummaryChip label="Orbs" value={selectedSummary?.orb_score ?? selectedProfile.orb_score} />
            </div>
          </div>
          <details className="mb-6 rounded-2xl border border-zinc-200 bg-zinc-50 p-4" open>
            <summary className="cursor-pointer select-none text-base font-semibold text-zinc-700">
              Stat Breakdown (Shared + Profile-only)
            </summary>
            <div className="mt-3 space-y-4">
              <div className="grid gap-2 text-xs text-zinc-600 sm:grid-cols-2">
                <div className="flex items-center gap-1">
                  <span>Shared Slots:</span>
                  <HelpTooltip text="How many slot assignments in this profile are shared with one or more other profiles." />
                  <span className="font-mono">{selectedSharedStats.shared_slot_count}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span>Profile-only Slots:</span>
                  <HelpTooltip text="How many slot assignments are unique to this profile and not shared with others." />
                  <span className="font-mono">{selectedSharedStats.specific_slot_count}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span>Shared Value:</span>
                  <HelpTooltip text="Total orb value contributed by shared slot assignments for this profile." />
                  <span className="font-mono">{rounded(selectedSharedStats.shared_total_value)}</span>
                </div>
                <div className="flex items-center gap-1">
                  <span>Profile-only Value:</span>
                  <HelpTooltip text="Total orb value contributed by this profile's non-shared slot assignments." />
                  <span className="font-mono">{rounded(selectedSharedStats.specific_total_value)}</span>
                </div>
                {hasSelectedSharedSlots && (
                  <>
                    <div className="flex items-center gap-1">
                      <span>Shared With:</span>
                      <HelpTooltip text="How often this profile shares with each other profile across shared slot rows." />
                      <span className="font-mono">
                        {selectedSharedStats.shared_with.length > 0
                          ? selectedSharedStats.shared_with
                              .map(([name, count]) => `${name}=${count}`)
                              .join(", ")
                          : "—"}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span>Compromise Loss:</span>
                      <HelpTooltip text="Estimated score tradeoff for this profile caused by enforcing shared choices instead of that profile's solo-best legal choice." />
                      <span className="font-mono">{rounded(selectedSharedStats.compromise_loss)}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <span>Cap-limited Shared Slots:</span>
                      <HelpTooltip text="Shared slots where this profile's preferred legal choice was blocked by set-piece cap constraints." />
                      <span className="font-mono">{selectedSharedStats.cap_limited_slots}</span>
                    </div>
                  </>
                )}
              </div>

              <div className="space-y-4">
                <LoadoutStatTables
                  sharedActiveSets={selectedSharedStats.shared_active_sets}
                  specificActiveSets={selectedSharedStats.specific_active_sets}
                  sharedTypeTotals={selectedSharedStats.shared_totals_by_type}
                  specificTypeTotals={selectedSharedStats.specific_totals_by_type}
                />
                <GateStatComparisonTable
                  sharedStats={selectedSharedStats.shared_level_gate_stats}
                  specificStats={selectedSharedStats.specific_level_gate_stats}
                />
              </div>
            </div>
          </details>
          <ProfileResults assignments={selectedProfile.assignments} />
        </div>
      </div>

      {(hasSharedSummary || runDiagnostics) && (
        <div className="mt-8 rounded-2xl border border-zinc-200 bg-zinc-50 p-4 space-y-3">
          <h3 className="text-base font-semibold">Advanced Diagnostics</h3>
          <details className="rounded-xl border border-zinc-200 bg-white p-3">
            <summary className="cursor-pointer select-none text-sm font-medium text-zinc-700">
              View advanced metrics
            </summary>
            <div className="mt-3 space-y-4 text-xs text-zinc-600">
              {hasSharedSummary && parsed.shared_summary && (
                <div className="space-y-2">
                  <div className="text-sm font-medium text-zinc-700">Shared Solving</div>
                  <div className="flex items-center gap-1">
                    <span>Compromise Loss:</span>
                    <HelpTooltip text="Estimated total score left on the table from selecting shared-compatible choices instead of each profile's solo-best legal choice." />
                    <span className="font-mono">{rounded(parsed.shared_summary.compromise_loss_total)}</span>
                  </div>
                  {Object.keys(parsed.shared_summary.cap_limited_slots_by_profile).length > 0 && (
                    <div className="flex items-center gap-1">
                      <span>Cap-limited Slots:</span>
                      <HelpTooltip text="Shared slot positions where the profile's higher-scoring option was blocked by set-piece cap constraints." />
                      <span className="font-mono">
                        {Object.entries(parsed.shared_summary.cap_limited_slots_by_profile)
                          .map(([name, count]) => `${name}=${count}`)
                          .join(", ")}
                      </span>
                    </div>
                  )}
                </div>
              )}

              {runDiagnostics && (
                <div className="space-y-2">
                  <div className="text-sm font-medium text-zinc-700">Whole Run</div>
                  <div className="space-y-1">
                    {orderedDiagnostics(runDiagnostics).map(([key, value]) => (
                      <div key={key} className="flex items-center gap-1">
                        <span>{titleCase(key)}:</span>
                        <HelpTooltip text={diagnosticTooltip(key)} />
                        <span className="font-mono">{formatDiagnosticValue(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </details>
        </div>
      )}
    </Section>
  );
}
