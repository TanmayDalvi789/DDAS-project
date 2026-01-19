/**
 * DecisionBadge Component
 * Color-coded status badge for ALLOW/WARN/BLOCK decisions
 */

interface DecisionBadgeProps {
  decision: "ALLOW" | "WARN" | "BLOCK" | "RUNNING" | "OFFLINE" | "DEGRADED";
  size?: "sm" | "md";
}

export function DecisionBadge({ decision, size = "md" }: DecisionBadgeProps) {
  const sizeClass = size === "sm" ? "text-xs px-2 py-1" : "text-sm px-3 py-1";

  let bgClass = "";
  let textClass = "";
  let borderClass = "";

  switch (decision) {
    case "ALLOW":
    case "RUNNING":
      bgClass = "bg-green-50";
      textClass = "text-green-700";
      borderClass = "border border-green-200";
      break;
    case "WARN":
    case "DEGRADED":
      bgClass = "bg-amber-50";
      textClass = "text-amber-700";
      borderClass = "border border-amber-200";
      break;
    case "BLOCK":
      bgClass = "bg-red-50";
      textClass = "text-red-700";
      borderClass = "border border-red-200";
      break;
    case "OFFLINE":
      bgClass = "bg-slate-100";
      textClass = "text-slate-600";
      borderClass = "border border-slate-200";
      break;
    default:
      bgClass = "bg-slate-100";
      textClass = "text-slate-600";
      borderClass = "border border-slate-200";
  }

  return (
    <span
      className={`badge ${sizeClass} ${bgClass} ${textClass} ${borderClass}`}
    >
      {decision}
    </span>
  );
}
