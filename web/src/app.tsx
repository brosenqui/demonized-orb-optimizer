import React from "react";
import Home from "./pages/Home";
import { Toaster } from "@/components/ui/sonner";

export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-50 to-zinc-100 text-zinc-800">
      <header className="max-w-6xl mx-auto px-5 py-6">
        <h1 className="text-2xl font-bold">🧮 Demonized Orb Optimizer</h1>
      </header>

      <Home />

      {/* Utility styles (Tailwind-based)
      <style>{`
        .input { @apply px-3 py-2 rounded-xl border border-zinc-300 bg-white shadow-sm w-full; }
        .btn { @apply px-3 py-2 rounded-xl bg-zinc-900 text-white hover:bg-zinc-800 active:scale-[0.99]; }
        .btn-subtle { @apply px-3 py-2 rounded-xl bg-zinc-100 hover:bg-zinc-200; }
        .codeblock { @apply p-3 rounded-xl bg-zinc-900 text-zinc-100 overflow-auto text-xs; }
      `}</style> */}

      {/* Global toaster for notifications */}
      <Toaster position="top-right" />
    </div>
  );
}
