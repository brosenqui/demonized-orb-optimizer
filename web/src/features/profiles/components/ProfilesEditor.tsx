import Section from "@/components/ui/Section";
import { Button } from "@/components/ui/button";
import type { CategoryRarity, OptimizeProfileIn } from "@/lib/types";
import { PRIORITY_TEMPLATES } from "@/lib/priorityTemplates";
import ProfileCardWithTemplates from "./ProfileCardWithTemplate";
import ShareablePicker from "./ShareablePicker";

type ProfilesEditorProps = {
  profiles: OptimizeProfileIn[];
  shareable: readonly string[];
  setShareable: (shareable: string[]) => void;
  onAddProfile: () => void;
  onUpdateProfile: (index: number, profile: OptimizeProfileIn) => void;
  onRemoveProfile: (index: number) => void;
  onSetCategory: (index: number, category: string, rarity: CategoryRarity | "") => void;
  availableSets: readonly string[];
  availableTypes: readonly string[];
};

export default function ProfilesEditor({
  profiles,
  shareable,
  setShareable,
  onAddProfile,
  onUpdateProfile,
  onRemoveProfile,
  onSetCategory,
  availableSets,
  availableTypes,
}: ProfilesEditorProps) {
  return (
    <Section
      title="Profiles"
      helpText="Define optimization profiles to guide orb selection priorities, type weights, and category rarity targets."
      actions={
        <div className="flex items-center gap-2">
          <ShareablePicker value={shareable} onChange={setShareable} />
          <Button onClick={onAddProfile}>Add Profile</Button>
        </div>
      }
    >
      <div className="space-y-4">
        {profiles.length === 0 && <p className="text-sm text-muted-foreground">No profiles yet.</p>}

        {profiles.map((profile, index) => (
          <ProfileCardWithTemplates
            key={index}
            value={profile}
            onChange={(next) => onUpdateProfile(index, next)}
            onRemove={() => onRemoveProfile(index)}
            onSetCategory={(category, rarity) => onSetCategory(index, category, rarity)}
            templates={PRIORITY_TEMPLATES}
            availableSets={availableSets}
            availableTypes={availableTypes}
          />
        ))}
      </div>
    </Section>
  );
}
