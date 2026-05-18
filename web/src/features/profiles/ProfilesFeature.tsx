import ProfilesEditor from "@/features/profiles/components/ProfilesEditor";
import { useAppState } from "@/app/AppStateProvider";
import { ORB_SETS, ORB_TYPES } from "@/lib/orbData";

export default function ProfilesFeature() {
  const {
    profiles,
    shareabilityMatrix,
    setShareabilityMatrix,
    addProfile,
    updateProfile,
    removeProfile,
    setProfileCategory,
  } = useAppState();

  return (
    <ProfilesEditor
      profiles={profiles}
      shareabilityMatrix={shareabilityMatrix}
      setShareabilityMatrix={setShareabilityMatrix}
      onAddProfile={addProfile}
      onUpdateProfile={updateProfile}
      onRemoveProfile={removeProfile}
      onSetCategory={setProfileCategory}
      availableSets={ORB_SETS}
      availableTypes={ORB_TYPES}
    />
  );
}
