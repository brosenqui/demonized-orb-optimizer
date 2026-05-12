import React from "react";
import { Button } from "@/components/ui/button";
import { Sparkles, Trash2 } from "lucide-react";
import type { OrbIn } from "@/lib/types";
import {
  TYPE_ICON,
  rarityCardClass,
  iconSizeForDensity,
  typeSizeForDensity,
  valueSizeForDensity,
  levelPillForDensity,
  setBadgeForDensity,
  tileChromeForDensity,
} from "./OrbDisplay";
import type { Density } from "./OrbDisplay";

type OrbTileProps = {
  orb: OrbIn;
  density?: Density;
  // Visibility overrides (by default cozy/compact hide)
  showLevel?: boolean;
  showSet?: boolean;
  showValue?: boolean;

  // Interactions (optional)
  onClick?: () => void;         // open edit in editor or open details in results
  onDelete?: () => void;        // show a hover delete button if provided
  clickable?: boolean;          // toggles cursor/keyboard handlers
};

export default function OrbTile({
  orb,
  density = "cozy",
  showLevel = false,
  showSet = false,
  showValue = false,
  onClick,
  onDelete,
  clickable = true,
}: OrbTileProps) {
  const cardCls = rarityCardClass[orb.rarity];
  const tileChrome = tileChromeForDensity(density);
  const iconSize = iconSizeForDensity(density);
  const typeSize = typeSizeForDensity(density);
  const valueSize = valueSizeForDensity(density);
  const levelPill = levelPillForDensity(density);
  const setBadge = setBadgeForDensity(density);
  const icon = TYPE_ICON[orb.type] ?? "🔮";
  const orbLabel = `${orb.rarity} ${orb.type} orb from ${orb.set}`;

  return (
    <div
      className={`group relative aspect-[1/1] ${tileChrome} ${cardCls} flex items-center justify-center select-none ${clickable ? "cursor-pointer" : ""}`}
      onClick={clickable ? onClick : undefined}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : -1}
      aria-label={clickable ? `Edit ${orbLabel}` : orbLabel}
      onKeyDown={
        clickable
          ? (e) => {
              if (e.key === "Enter") onClick?.();
              if (e.key === " ") {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
    >
      {/* Hover-only delete top-left */}
      {onDelete && (
        <div className="absolute top-2 left-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            variant="destructive"
            size="icon"
            className="h-7 w-7"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            title="Delete orb"
            aria-label={`Delete ${orbLabel}`}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Awakened + level pills top-right */}
      {(orb.awakened > 0 || (showLevel && orb.level > 0)) && (
        <div className="absolute top-2 right-2 flex flex-col items-end gap-1">
          {orb.awakened > 0 && (
            <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
              <Sparkles className="h-3 w-3" />
              A+{orb.awakened}
            </span>
          )}
          {showLevel && orb.level > 0 && <span className={levelPill}>+{orb.level}</span>}
        </div>
      )}

      {/* Set badge bottom-left */}
      {showSet && (
        <div className="absolute bottom-2 left-2">
          <span className={setBadge}>{orb.set}</span>
        </div>
      )}

      {/* Center content */}
      <div className="pointer-events-none flex flex-col items-center justify-center text-center">
        <div className={iconSize + " leading-none"}>{icon}</div>
        <div className={"mt-1 font-semibold " + typeSize}>{orb.type}</div>
        {showValue && <div className={"opacity-70 " + valueSize}>+{orb.value}</div>}
      </div>
    </div>
  );
}
