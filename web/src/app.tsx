import Home from "./pages/Home";
import { Toaster } from "@/components/ui/sonner";
import { AppStateProvider } from "@/app/AppStateProvider";

export default function App() {
  return (
    <AppStateProvider>
      <div className="min-h-screen bg-gradient-to-b from-zinc-50 to-zinc-100 text-zinc-800">
        <header className="max-w-6xl mx-auto px-5 py-6">
          <h1 className="text-2xl font-bold">🧮 Demonized Orb Optimizer</h1>
        </header>

        <Home />

        <Toaster position="top-right" />
      </div>
    </AppStateProvider>
  );
}
