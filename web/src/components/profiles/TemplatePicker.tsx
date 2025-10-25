// src/components/profiles/PriorityTemplatePicker.tsx
import * as React from "react";
import { Button } from "../ui/button";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "../ui/select";
import type { PriorityTemplate } from "../../lib/priorityTemplates";

export default function PriorityTemplatePicker({
  templates,
  value,
  onChange,
  onApply,
  size = "default",
  alignApply = false,
}: {
  templates: PriorityTemplate[];
  value?: string;
  onChange: (id: string) => void;
  onApply?: () => void;
  size?: "default" | "sm";
  alignApply?: boolean; // if true, put Apply on the right
}) {
  const hasValue = Boolean(value);

  return (
    <div className={`flex items-center gap-2 ${alignApply ? "justify-end" : ""}`}>
      <Select value={value || ""} onValueChange={onChange}>
        <SelectTrigger className={size === "sm" ? "h-8 w-56" : "h-9 w-60"}>
          <SelectValue placeholder="— Template —" />
        </SelectTrigger>
        <SelectContent>
          {templates.map((t) => (
            <SelectItem key={t.id} value={t.id}>
              {t.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {onApply && (
        <Button
          variant="secondary"
          size={size === "sm" ? "sm" : "default"}
          disabled={!hasValue}
          onClick={onApply}
        >
          Apply
        </Button>
      )}
    </div>
  );
}
