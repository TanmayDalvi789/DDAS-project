/**
 * StatCard Component
 * Displays a single statistic with subtle hover elevation
 */

interface StatCardProps {
  label: string;
  value: number | string;
  trend?: number;
  trendLabel?: string;
}

export function StatCard({ label, value, trend, trendLabel }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="text-sm font-medium text-slate-500 mb-2">{label}</div>
      <div className="text-3xl font-semibold text-slate-900 mb-4">{value}</div>
      {trend !== undefined && trendLabel && (
        <div className="text-xs text-slate-500">
          {trend > 0 ? "+" : ""}{trend}% {trendLabel}
        </div>
      )}
    </div>
  );
}
