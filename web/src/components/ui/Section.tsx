import React from "react";
import { Card } from "@/components/ui/card";

export default function Section({
  title,
  children,
  actions,
}: {
  title: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <Card className="bg-white/70 backdrop-blur rounded-2xl shadow p-5 border">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xl font-semibold text-zinc-800">{title}</h2>
        {actions}
      </div>
      {children}
    </Card>
  );
}
