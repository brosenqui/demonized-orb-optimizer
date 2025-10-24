// src/components/ResultViewer.tsx
import React, { useState } from "react";
import Section from "../ui/Section";
import ProfileResult from "./ProfileResults";
import type { OptimizeResponse } from "@/lib/types";
import { parseResultsFromRaw } from "@/lib/resultParser";
import type { Density } from "@/components/orbs/orbDisplay";
import {
  Select as UiSelect,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";

function num(n: unknown) {
  return typeof n === "number" ? Number(n.toFixed(6)) : n;
}

function Chip({
  label,
  value,
}: {
  label: string;
  value: number | null | undefined;
}) {
  if (value == null) return null;
  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-zinc-100 border border-zinc-200">
      <span className="text-zinc-600">{label}:</span>
      <span className="font-mono">{num(value)}</span>
    </span>
  );
}

export default function ResultViewer({
  data,
  loading,
  error,
}: {
  data: OptimizeResponse | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <Section title="Results"><p>Running optimization…</p></Section>;
  if (error) return <Section title="Results"><p className="text-red-600">{error}</p></Section>;
  if (!data) return <Section title="Results"><p className="text-sm text-zinc-500">No results yet.</p></Section>;

  const raw = data.result?.raw;
  const parsed = parseResultsFromRaw(raw);

  if (!parsed || !parsed.profiles || parsed.profiles.length === 0) {
    return (
      <Section title="Results">
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <h4 className="font-semibold mb-2">Summary</h4>
            <pre className="codeblock">{JSON.stringify(data.result.summary, null, 2)}</pre>
          </div>
          <div>
            <h4 className="font-semibold mb-2">Raw</h4>
            <pre className="codeblock">{JSON.stringify(data.result.raw, null, 2)}</pre>
          </div>
        </div>
      </Section>
    );
  }

  return (
    <Section
      title="Results"
    >
      {/* Global combined score */}
      {parsed.combined_score != null && (
        <div className="text-sm text-zinc-600 mb-3">
          Combined Score: <span className="font-mono">{num(parsed.combined_score)}</span>
        </div>
      )}

      {/* Detailed per-profile sections */}
      <div className="space-y-8">
        {parsed.profiles.map((p, idx) => (
          <div key={`${p.name}-${idx}`} className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold">Profile: {p.name}</h3>
              <div className="flex flex-wrap gap-2">
                <Chip label="Total" value={p.score} />
                <Chip label="Sets" value={p.set_score} />
                <Chip label="Orbs" value={p.orb_score} />
              </div>
            </div>

            <ProfileResult
              profileName={p.name}
              assignments={p.assignments}
            />
          </div>
        ))}
      </div>
    </Section>
  );
}
