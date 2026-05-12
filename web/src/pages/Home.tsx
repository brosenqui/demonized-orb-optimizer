import OrbsFeature from "@/features/orbs/OrbsFeature";
import ProfilesFeature from "@/features/profiles/ProfilesFeature";
import ResultsFeature from "@/features/results/ResultsFeature";
import RunPanel from "@/app/RunPanel";

export default function Home() {
  return (
    <div className="max-w-6xl mx-auto px-5 pb-10 space-y-6">
      <OrbsFeature />
      <ProfilesFeature />
      <RunPanel />
      <ResultsFeature />
    </div>
  );
}
