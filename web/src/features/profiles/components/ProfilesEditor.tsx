import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import Section from "@/components/ui/Section";
import { Button } from "@/components/ui/button";
import type { CategoryRarity, OptimizeProfileIn, ShareabilityMatrix } from "@/lib/types";
import { PRIORITY_TEMPLATES } from "@/lib/priorityTemplates";
import ProfileCardWithTemplates from "./ProfileCardWithTemplate";
import ShareabilityMatrixEditor from "./ShareabilityMatrixEditor";

type ProfilesEditorProps = {
  profiles: OptimizeProfileIn[];
  shareabilityMatrix: ShareabilityMatrix;
  setShareabilityMatrix: (shareabilityMatrix: ShareabilityMatrix) => void;
  onAddProfile: () => void;
  onUpdateProfile: (index: number, profile: OptimizeProfileIn) => void;
  onRemoveProfile: (index: number) => void;
  onSetCategory: (index: number, category: string, rarity: CategoryRarity | "") => void;
  availableSets: readonly string[];
  availableTypes: readonly string[];
};

export default function ProfilesEditor({
  profiles,
  shareabilityMatrix,
  setShareabilityMatrix,
  onAddProfile,
  onUpdateProfile,
  onRemoveProfile,
  onSetCategory,
  availableSets,
  availableTypes,
}: ProfilesEditorProps) {
  const [collapsedProfiles, setCollapsedProfiles] = useState<Record<number, boolean>>({});

  return (
    <Section
      title="Profiles"
      helpText="Define optimization profiles to guide orb selection priorities, type weights, and category rarity targets."
      actions={
        <div className="flex items-center gap-2">
          <Button onClick={onAddProfile}>Add Profile</Button>
        </div>
      }
    >
      <div className="space-y-4">
        <ShareabilityMatrixEditor
          profiles={profiles}
          value={shareabilityMatrix}
          onChange={setShareabilityMatrix}
        />
        {profiles.length === 0 && <p className="text-sm text-muted-foreground">No profiles yet.</p>}

        {profiles.map((profile, index) => {
          const profileTitle = profile.name.trim() || `Profile ${index + 1}`;
          const isCollapsed = collapsedProfiles[index] ?? false;
          return (
            <div
              key={index}
              className="rounded-2xl border border-zinc-200 bg-white/70 p-3 shadow-sm backdrop-blur"
            >
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-base font-semibold">{profileTitle}</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() =>
                    setCollapsedProfiles((current) => ({
                      ...current,
                      [index]: !isCollapsed,
                    }))
                  }
                  aria-expanded={!isCollapsed}
                  aria-label={isCollapsed ? `Expand profile ${profileTitle}` : `Collapse profile ${profileTitle}`}
                  title={isCollapsed ? `Expand profile ${profileTitle}` : `Collapse profile ${profileTitle}`}
                  className="h-7 w-7 p-0"
                >
                  {isCollapsed ? (
                    <ChevronDown className="h-4 w-4" aria-hidden="true" />
                  ) : (
                    <ChevronUp className="h-4 w-4" aria-hidden="true" />
                  )}
                </Button>
              </div>
              {!isCollapsed && (
                <div className="mt-3">
                  <ProfileCardWithTemplates
                    value={profile}
                    onChange={(next) => onUpdateProfile(index, next)}
                    onRemove={() => onRemoveProfile(index)}
                    onSetCategory={(category, rarity) => onSetCategory(index, category, rarity)}
                    templates={PRIORITY_TEMPLATES}
                    availableSets={availableSets}
                    availableTypes={availableTypes}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Section>
  );
}
