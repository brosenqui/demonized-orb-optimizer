import React from "react";
import { Button } from "../ui/button";
import { Trash2 } from "lucide-react";
import type { OrbIn } from "../../lib/types";
import {
  TYPE_ICON,
  rarityCardClass,
  Density,
  iconSizeForDensity,
  typeSizeForDensity,
  valueSizeForDensity,
  levelPillForDensity,
  setBadgeForDensity,
  tileChromeForDensity,
} from "./orbDisplay";

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

  return (
    <div
      className={`group relative aspect-[1/1] ${tileChrome} ${cardCls} flex items-center justify-center select-none ${clickable ? "cursor-pointer" : ""}`}
      onClick={clickable ? onClick : undefined}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : -1}
      onKeyDown={
        clickable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") onClick?.();
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
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Level pill top-right */}
      {showLevel && orb.level > 0 && (
        <div className="absolute top-2 right-2">
          <span className={levelPill}>+{orb.level}</span>
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
