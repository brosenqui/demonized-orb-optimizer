import ResultViewer from "@/features/results/components/ResultViewer";
import { useAppState } from "@/app/AppStateProvider";

export default function ResultsFeature() {
  const { result, loading, error } = useAppState();
  return <ResultViewer data={result} loading={loading} error={error} />;
}
