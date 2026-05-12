import ProfilesEditor from "@/features/profiles/components/ProfilesEditor";
import { useAppState } from "@/app/AppStateProvider";
import { ORB_SETS, ORB_TYPES } from "@/lib/orbData";

export default function ProfilesFeature() {
  const {
    profiles,
    shareable,
    setShareable,
    addProfile,
    updateProfile,
    removeProfile,
    setProfileCategory,
  } = useAppState();

  return (
    <ProfilesEditor
      profiles={profiles}
      shareable={shareable}
      setShareable={setShareable}
      onAddProfile={addProfile}
      onUpdateProfile={updateProfile}
      onRemoveProfile={removeProfile}
      onSetCategory={setProfileCategory}
      availableSets={ORB_SETS}
      availableTypes={ORB_TYPES}
    />
  );
}
