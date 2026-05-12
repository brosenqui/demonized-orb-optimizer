// src/components/profiles/ProfileCardWithTemplates.tsx
import * as React from "react";
import ProfileCard from "./ProfileCard";
import { Label } from "@/components/ui/label";
import PriorityTemplatePicker from "./TemplatePicker";
import { applyTemplateToProfile } from "@/lib/applyTemplate";
import type { PriorityTemplate } from "@/lib/priorityTemplates";
import type { CategoryRarity, OptimizeProfileIn } from "@/lib/types";

type BaseProps = {
  value: OptimizeProfileIn;
  onChange: (next: OptimizeProfileIn) => void;
  onRemove: () => void;
  onSetCategory: (cat: string, rarity: CategoryRarity | "") => void;
  availableSets: readonly string[];
  availableTypes: readonly string[];
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
    const next = applyTemplateToProfile(value, tpl);
    onChange(next);
  }, [tpl, value, onChange]);

  return (
    <div className="space-y-2">
      {templates.length > 0 && (
        <div className="flex items-center gap-3 px-1">
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

      <ProfileCard value={value} onChange={onChange} {...rest} />
    </div>
  );
}
