import React from "react";
import Section from "../ui/Section";
import ProfileCard from "./ProfileCard";
import type { OptimizeProfileIn, Rarity } from "../../lib/types";
import { Button } from "../ui/button";
import ShareablePicker from "./ShareablePicker";

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
  const blank: OptimizeProfileIn = {
    name: "New Profile",
    weight: 1,
    objective: "sets-first",
    power: 2.0,
    epsilon: 0.02,
    set_priority: {},
    orb_weights: {},
    orb_level_weights: {},
    categories: {}, // ensure new profiles start with a categories object
  };

  function update(i: number, patch: Partial<OptimizeProfileIn>) {
    const next = [...profiles];
    next[i] = { ...next[i], ...patch } as OptimizeProfileIn;
    setProfiles(next);
  }

  /**
   * When a profile sets a category rarity, if that category is shareable,
   * propagate the same rarity to ALL profiles.
   */
  function handleSetCategory(pIndex: number, cat: string, rarity: Rarity | "") {
    // Update the target profile first
    const next = profiles.map((p, idx) => {
      if (idx !== pIndex) return p;
      const cats = { ...(p.categories ?? {}) };
      if (!rarity) delete cats[cat];
      else cats[cat] = rarity;
      return { ...p, categories: cats };
    });

    // If cat is shareable, propagate to every other profile
    if (shareable.includes(cat)) {
      for (let i = 0; i < next.length; i++) {
        if (i === pIndex) continue;
        const cats = { ...(next[i].categories ?? {}) };
        if (!rarity) delete cats[cat];
        else cats[cat] = rarity;
        next[i] = { ...next[i], categories: cats };
      }
    }

    setProfiles(next);
  }

  return (
    <Section
      title="Profiles"
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
          <ProfileCard
            key={i}
            value={p}
            onChange={(np) => update(i, np)}
            onRemove={() =>
              setProfiles(profiles.filter((_, j) => j !== i))
            }
            onSetCategory={(cat, rarity) => handleSetCategory(i, cat, rarity)}
            availableSets={availableSets}
            availableTypes={availableTypes}
          />
        ))}
      </div>
    </Section>
  );
}
