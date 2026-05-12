import Section from "@/components/ui/Section";
import ProfileResults from "@/features/results/components/ProfileResults";
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

function sortedNumericEntries(values: Record<string, number>): Array<[string, number]> {
  return Object.entries(values).sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]));
}

type ResultViewerProps = {
  data: OptimizeResponse | null;
  loading: boolean;
  error: string | null;
};

export default function ResultViewer({ data, loading, error }: ResultViewerProps) {
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

  return (
    <Section title="Results">
      {parsed.combined_score != null && (
        <div className="mb-3 text-sm text-zinc-600">
          Combined Score: <span className="font-mono">{rounded(parsed.combined_score)}</span>
        </div>
      )}
      <div className="mb-3 text-sm text-zinc-600">
        Coverage:{" "}
        <span className="font-mono">
          {parsed.filled_slots}/{parsed.requested_slots}
        </span>
        {parsed.is_partial ? " (partial)" : " (complete)"}
      </div>

      {parsed.shared_summary && (
        <div className="mb-6 rounded-2xl border border-zinc-200 bg-zinc-50 p-4 space-y-3">
          <h3 className="text-base font-semibold">Shared Slot Summary</h3>
          <div className="text-xs text-zinc-600">
            Coverage: {parsed.shared_summary.filled_slots}/{parsed.shared_summary.requested_slots}
            {parsed.shared_summary.is_partial ? " (partial)" : " (complete)"}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <div className="mb-1 text-sm font-medium">Shared Active Sets</div>
              {sortedNumericEntries(parsed.shared_summary.active_sets).length === 0 ? (
                <p className="text-xs text-zinc-500">None</p>
              ) : (
                <ul className="space-y-1 text-xs text-zinc-700">
                  {sortedNumericEntries(parsed.shared_summary.active_sets).map(([setName, count]) => (
                    <li key={setName}>
                      {setName}: <span className="font-mono">{count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <div className="mb-1 text-sm font-medium">Shared Totals by Type</div>
              {sortedNumericEntries(parsed.shared_summary.totals_by_type).length === 0 ? (
                <p className="text-xs text-zinc-500">None</p>
              ) : (
                <ul className="space-y-1 text-xs text-zinc-700">
                  {sortedNumericEntries(parsed.shared_summary.totals_by_type).map(([type, total]) => (
                    <li key={type}>
                      {type}: <span className="font-mono">{rounded(total)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          <details className="rounded-xl border border-zinc-200 bg-white p-3">
            <summary className="cursor-pointer select-none text-sm font-medium text-zinc-700">
              Advanced shared diagnostics
            </summary>
            <div className="mt-3 space-y-2 text-xs text-zinc-600">
              <div>
                Profile Coverage: {parsed.shared_summary.filled_positions}/
                {parsed.shared_summary.requested_positions}
              </div>
              <div>
                Compromise Loss:{" "}
                <span className="font-mono">{rounded(parsed.shared_summary.compromise_loss_total)}</span>
              </div>
              {Object.keys(parsed.shared_summary.cap_limited_slots_by_profile).length > 0 && (
                <div>
                  Cap-limited Slots:{" "}
                  {Object.entries(parsed.shared_summary.cap_limited_slots_by_profile)
                    .map(([name, count]) => `${name}=${count}`)
                    .join(", ")}
                </div>
              )}
            </div>
          </details>
        </div>
      )}

      <div className="space-y-8">
        {parsed.profiles.map((profile, index) => {
          const summary = summaries[profile.name];
          return (
            <div key={`${profile.name}-${index}`} className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold">Profile: {profile.name}</h3>
                <div className="flex flex-wrap gap-2">
                  <SummaryChip label="Total" value={summary?.score ?? profile.score} />
                  <SummaryChip label="Sets" value={summary?.set_score ?? profile.set_score} />
                  <SummaryChip label="Orbs" value={summary?.orb_score ?? profile.orb_score} />
                </div>
              </div>
              <div className="text-xs text-zinc-500">
                Coverage: {profile.filled_slots}/{profile.requested_slots}
                {profile.is_partial ? " (partial)" : " (complete)"}
              </div>
              <ProfileResults assignments={profile.assignments} />
            </div>
          );
        })}
      </div>
    </Section>
  );
}
