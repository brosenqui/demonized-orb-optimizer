// src/components/profiles/ProfileCardWithTemplates.tsx
import * as React from "react";
import ProfileCard from "./ProfileCard";
import { Label } from "../ui/label";
import PriorityTemplatePicker from "./TemplatePicker";
import { applyTemplateToProfileDestructive } from "../../lib/applyTemplate";
import type { PriorityTemplate } from "../../lib/priorityTemplates";
import type { OptimizeProfileIn, Rarity } from "../../lib/types";

type BaseProps = {
  value: OptimizeProfileIn;
  onChange: (next: OptimizeProfileIn) => void;
  onRemove: () => void;
  onSetCategory: (cat: string, rarity: Rarity) => void;
  availableSets: string[];
  availableTypes: string[];
};

type TemplateProps = {
  templates?: PriorityTemplate[];
};

type Props = BaseProps & TemplateProps;

export default function ProfileCardWithTemplates(props: Props) {
  const { value, onChange, templates = [], ...rest } = props;

  const [localTplId, setLocalTplId] = React.useState<string>("");

  const tpl = React.useMemo(
    () => templates.find((t) => t.id === localTplId),
    [templates, localTplId]
  );

  const handleApply = React.useCallback(() => {
    if (!tpl) return;
    const next = applyTemplateToProfileDestructive(value, tpl);
    onChange(next);
  }, [tpl, value, onChange]);

  return (
    <div className="rounded-2xl border p-4 space-y-4">
      {templates.length > 0 && (
        <div className="flex items-center gap-3">
          <Label className="min-w-20">Template</Label>
          <PriorityTemplatePicker
            templates={templates}
            value={localTplId}
            onChange={setLocalTplId}
            onApply={handleApply}
            size="sm"
          />
        </div>
      )}

      {/* your original card */}
      <ProfileCard value={value} onChange={onChange} {...rest} />
    </div>
  );
}
