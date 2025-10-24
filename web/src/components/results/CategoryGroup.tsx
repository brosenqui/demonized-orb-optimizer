import React from "react";
import OrbTile from "./OrbTile";
import type { CategoryResult } from "@/lib/resultParser";

export default function CategoryGroup({ cat }: { cat: CategoryResult }) {
  return (
    <div className="rounded-2xl border p-3 bg-white/60">
      <div className="flex items-center justify-between mb-2">
        <div className="font-semibold">{cat.category}</div>
        {cat.slots != null && (
          <div className="text-xs text-zinc-500">
            Slots: <span className="font-mono">{cat.slots}</span>
          </div>
        )}
      </div>
      {cat.orbs?.length ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {cat.orbs.map((o, i) => (
            <OrbTile key={i} orb={o} />
          ))}
        </div>
      ) : (
        <div className="text-sm text-zinc-500">No orbs assigned.</div>
      )}
    </div>
  );
}
