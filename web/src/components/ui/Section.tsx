import React from "react";
import { Card } from "@/components/ui/card";
import { HelpTooltip } from "./helpToolTip";

export default function Section({
  title,
  children,
  actions,
  helpText,
}: {
  title: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
  helpText?: string;
}) {
  return (
    <Card className="bg-white/70 backdrop-blur rounded-2xl shadow p-5 border">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <h2 className="text-xl font-semibold text-zinc-800">{title}</h2>
          {helpText && <HelpTooltip text={helpText} />}
        </div>
        {actions}
      </div>

      {children}
    </Card>
  );
}
