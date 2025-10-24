// Put icons in /public/icons/orbs/<lowercased-type>.png
// Example: Flame -> /icons/orbs/flame.png
export function orbIconSrc(type: string) {
  const safe = (type || "").toLowerCase().replace(/\s+/g, "-");
  return `/icons/orbs/${safe}.png`;
}
