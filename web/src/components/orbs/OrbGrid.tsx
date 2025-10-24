import React from "react";
import OrbTile from "./OrbTile";
import type { OrbIn } from "../../lib/types";
import {
  Density,
  gridClassForDensity,
  showDetailsForDensity,
} from "./OrbDisplay";

type OrbGridProps = {
  orbs: OrbIn[];
  density?: Density;

  // Optional overrides; if not provided, we auto-hide in cozy/compact
  showLevel?: boolean;
  showSet?: boolean;
  showValue?: boolean;

  // Interactions
  onTileClick?: (index: number) => void;
  onTileDelete?: (index: number) => void;

  // Layout
  className?: string;
};

export default function OrbGrid({
  orbs,
  density = "cozy",
  showLevel,
  showSet,
  showValue,
  onTileClick,
  onTileDelete,
  className = "",
}: OrbGridProps) {
  const gridCls = gridClassForDensity(density);
  const defaults = showDetailsForDensity(density);
  const vis = {
    showLevel: showLevel ?? defaults.showLevel,
    showSet: showSet ?? defaults.showSet,
    showValue: showValue ?? defaults.showValue,
  };

  return (
    <div className={`${gridCls} ${className}`}>
      {orbs.map((o, i) => (
        <OrbTile
          key={i}
          orb={o}
          density={density}
          showLevel={vis.showLevel}
          showSet={vis.showSet}
          showValue={vis.showValue}
          onClick={onTileClick ? () => onTileClick(i) : undefined}
          onDelete={onTileDelete ? () => onTileDelete(i) : undefined}
          clickable={!!onTileClick}
        />
      ))}
    </div>
  );
}
