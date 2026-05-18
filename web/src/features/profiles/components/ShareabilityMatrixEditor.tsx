import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { HelpTooltip } from "@/components/ui/helpToolTip";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { CATEGORIES } from "@/lib/categoryData";
import type { OptimizeProfileIn, ShareabilityMatrix } from "@/lib/types";
import { Check, X } from "lucide-react";

type Props = {
  profiles: readonly OptimizeProfileIn[];
  value: ShareabilityMatrix;
  onChange: (next: ShareabilityMatrix) => void;
};

function profileLabel(profile: OptimizeProfileIn, index: number): string {
  const trimmed = profile.name.trim();
  return trimmed.length > 0 ? trimmed : `Profile ${index + 1}`;
}

export default function ShareabilityMatrixEditor({ profiles, value, onChange }: Props) {
  if (profiles.length === 0) return null;

  const profileRows = profiles.map((profile, index) => ({
    key: profile.name,
    name: profile.name,
    label: profileLabel(profile, index),
  }));

  const setCell = (category: string, profileName: string, enabled: boolean) => {
    const next: ShareabilityMatrix = {
      ...value,
      [category]: {
        ...(value[category] ?? {}),
        [profileName]: enabled,
      },
    };
    onChange(next);
  };

  const setRow = (category: string, enabled: boolean) => {
    const nextRow: Record<string, boolean> = {};
    for (const profile of profiles) {
      nextRow[profile.name] = enabled;
    }
    onChange({
      ...value,
      [category]: nextRow,
    });
  };

  const setAll = (enabled: boolean) => {
    const next: ShareabilityMatrix = { ...value };
    for (const category of CATEGORIES) {
      next[category] = {};
      for (const profile of profiles) {
        next[category][profile.name] = enabled;
      }
    }
    onChange(next);
  };

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white/70 p-3 shadow-sm backdrop-blur">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold">Shareability Matrix</h3>
            <HelpTooltip text="Checked means the profile must use the same orb as other checked profiles for each slot in that category. Unchecked means that profile fills those slots independently." />
          </div>
          <p className="text-xs text-muted-foreground">
            Checked profiles are strictly linked per slot for that category and must receive the same
            orb.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => setAll(true)}>
            Enable all
          </Button>
          <Button size="sm" variant="outline" onClick={() => setAll(false)}>
            Disable all
          </Button>
        </div>
      </div>

      <div className="overflow-auto rounded-xl border border-zinc-200">
        <table className="min-w-full table-fixed border-collapse text-sm">
          <thead className="bg-zinc-50/80">
            <tr>
              <th className="sticky left-0 z-20 border-b border-r border-zinc-200 bg-zinc-50/95 px-3 py-2 text-left font-medium">
                Category
              </th>
              {profileRows.map((profile) => (
                <th
                  key={profile.key}
                  className="w-28 border-b border-r border-zinc-200 px-3 py-2 text-center font-medium"
                >
                  {profile.label}
                </th>
              ))}
              <th className="border-b border-zinc-200 px-3 py-2 text-right font-medium">
                <span className="inline-flex items-center gap-1">
                  <span>Row actions</span>
                  <HelpTooltip text="Use check to enable sharing for all profiles in this category row, or x to disable all." />
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {CATEGORIES.map((category) => {
              return (
                <tr key={category}>
                  <th
                    scope="row"
                    className="sticky left-0 z-10 border-b border-r border-zinc-200 bg-white/95 px-3 py-2 text-left font-medium"
                  >
                    {category}
                  </th>
                  {profileRows.map((profile) => {
                    const checked = Boolean(value?.[category]?.[profile.name]);
                    return (
                      <td
                        key={`${category}-${profile.key}`}
                        className={[
                          "w-28 border-b border-r border-zinc-200 px-3 py-2 text-center align-middle",
                          checked ? "bg-zinc-50/70" : "bg-white",
                        ].join(" ")}
                      >
                        <div className="flex items-center justify-center">
                          <Checkbox
                            checked={checked}
                            onCheckedChange={(nextChecked) =>
                              setCell(category, profile.name, Boolean(nextChecked))
                            }
                            aria-label={`Require shared orb for ${category} category on ${profile.label}`}
                          />
                        </div>
                      </td>
                    );
                  })}
                  <td className="border-b border-zinc-200 px-3 py-2">
                    <TooltipProvider>
                      <div className="flex justify-end gap-1">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-7 w-7 rounded-md border border-transparent hover:border-zinc-200"
                              onClick={() => setRow(category, true)}
                              aria-label={`Enable sharing for all profiles on ${category}`}
                            >
                              <Check />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent side="top" className="text-xs">
                            Enable all for {category}
                          </TooltipContent>
                        </Tooltip>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-7 w-7 rounded-md border border-transparent text-zinc-600 hover:border-zinc-200 hover:text-zinc-900"
                              onClick={() => setRow(category, false)}
                              aria-label={`Disable sharing for all profiles on ${category}`}
                            >
                              <X />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent side="top" className="text-xs">
                            Disable all for {category}
                          </TooltipContent>
                        </Tooltip>
                      </div>
                    </TooltipProvider>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
