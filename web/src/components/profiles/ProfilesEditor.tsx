// src/components/profiles/ProfilesEditor.tsx
import React from "react";
import Section from "../ui/Section";
import ProfileCardWithTemplates from "./ProfileCardWithTemplate";
import type { OptimizeProfileIn, Rarity } from "../../lib/types";
import { Button } from "../ui/button";
import ShareablePicker from "./ShareablePicker";
import { PRIORITY_TEMPLATES, PROFILE_DEFAULTS } from "../../lib/priorityTemplates";
import { applyTemplateToProfile } from "../../lib/applyTemplate";

type Props = {
  profiles: OptimizeProfileIn[];
  setProfiles: (p: OptimizeProfileIn[]) => void;

  shareable: string[];
  setShareable: (s: string[]) => void;

  availableSets: string[];
  availableTypes: string[];
};

export default function ProfilesEditor({
  profiles,
  setProfiles,
  shareable,
  setShareable,
  availableSets,
  availableTypes,
}: Props) {
  function update(index: number, np: OptimizeProfileIn) {
    const next = [...profiles];
    next[index] = np;
    setProfiles(next);
  }

  function handleSetCategory(index: number, cat: string, rarity: Rarity) {
    const p = profiles[index];
    const updated: OptimizeProfileIn = {
      ...p,
      categories: { ...(p.categories || {}), [cat]: rarity },
    };

    let next = [...profiles];
    next[index] = updated;

    if (shareable.includes(cat)) {
      next = next.map((prof, i) =>
        i === index
          ? updated
          : { ...prof, categories: { ...(prof.categories || {}), [cat]: rarity } }
      );
    }

    setProfiles(next);
  }

  // Bulk-apply template (destructive)
  const [tplId, setTplId] = React.useState<string>("");

  function applyTemplateToAll() {
    const tpl = PRIORITY_TEMPLATES.find((t) => t.id === tplId);
    if (!tpl) return;

    const next = profiles.map((p) => applyTemplateToProfile(p, tpl));
    setProfiles(next);
  }

  const blank: OptimizeProfileIn = { ...PROFILE_DEFAULTS };

  return (
    <Section
      title="Profiles"
      helpText="Define optimization profiles to guide how orbs are selected during optimization. Each profile can prioritize different sets, orb types, and objectives."
      actions={
        <div className="flex items-center gap-2">
          <ShareablePicker value={shareable} onChange={setShareable} />
          <Button onClick={() => setProfiles([...profiles, { ...blank }])}>
            Add Profile
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {profiles.length === 0 && (
          <p className="text-sm text-muted-foreground">No profiles yet.</p>
        )}

        {profiles.map((p, i) => (
          <ProfileCardWithTemplates
            key={i}
            value={p}
            onChange={(np) => update(i, np)}
            onRemove={() => setProfiles(profiles.filter((_, j) => j !== i))}
            onSetCategory={(cat, rarity) => handleSetCategory(i, cat, rarity)}
            templates={PRIORITY_TEMPLATES}
            availableSets={availableSets}
            availableTypes={availableTypes}
          />
        ))}
      </div>
    </Section>
  );
}
