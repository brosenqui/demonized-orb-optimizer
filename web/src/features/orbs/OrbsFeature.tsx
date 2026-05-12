import OrbsEditor from "@/features/orbs/components/OrbsEditor";
import { useAppState } from "@/app/AppStateProvider";

export default function OrbsFeature() {
  const { orbs, setOrbs } = useAppState();
  return <OrbsEditor orbs={orbs} setOrbs={setOrbs} />;
}
