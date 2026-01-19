/**
 * Overview Page (Home)
 * Dashboard home with stats, charts, and recent events
 */

"use client";

import { useState } from "react";
import { StatCard } from "./components/StatCard";
import { DataTable } from "./components/DataTable";
import { DecisionBadge } from "./components/DecisionBadge";
import { SectionHeader } from "./components/SectionHeader";
import { ErrorBanner } from "./components/ErrorBanner";
import { StatsGridSkeleton, SkeletonLoader } from "./components/SkeletonLoader";
import { useDashboardOverview, useEvents } from "./lib/hooks";

export default function Home() {
  const [dismissError, setDismissError] = useState(false);
  const { data: overviewData, loading: loadingOverview, error: overviewError } = useDashboardOverview();
  const { data: eventsData, loading: loadingEvents, error: eventsError } = useEvents({ limit: 5 });

  // Extract stats from API response
  const stats = overviewData?.stats || {
    activeAgents: 0,
    totalEvents: 0,
    warnCount: 0,
    blockCount: 0,
  };

  // Extract recent events from API response
  const recentEvents = eventsData?.events || [];
  const chartData = overviewData?.chartData || [];

  // Combine errors for display
  const allErrors = [overviewError, eventsError].filter(Boolean);

  return (
    <div>
      <SectionHeader
        title="Overview"
        subtitle="System health and recent activity"
      />

      {/* Error Banner */}
      {allErrors.length > 0 && !dismissError && (
        <ErrorBanner 
          error={allErrors[0]!} 
          onDismiss={() => setDismissError(true)}
        />
      )}

      {/* Loading or Stats Grid */}
      {loadingOverview ? (
        <StatsGridSkeleton />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            label="Active Agents"
            value={stats.activeAgents || 0}
            trend={5}
            trendLabel="vs last 7 days"
          />
          <StatCard
            label="Total Events"
            value={stats.totalEvents || 0}
            trend={12}
            trendLabel="vs last 7 days"
          />
          <StatCard
            label="Warnings"
            value={stats.warnCount || 0}
            trend={-3}
            trendLabel="vs last 7 days"
          />
          <StatCard
            label="Blocks"
            value={stats.blockCount || 0}
            trend={1}
            trendLabel="vs last 7 days"
          />
        </div>
      )}

      {/* Chart Placeholder */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 mb-8 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          Events Over Time
        </h2>
        {loadingOverview ? (
          <div className="h-64 bg-slate-100 rounded-lg flex items-center justify-center">
            <div className="text-slate-400">Loading chart...</div>
          </div>
        ) : chartData.length > 0 ? (
          <div className="h-64 bg-slate-100 rounded-lg flex items-center justify-center">
            <div className="text-slate-400">Chart data available ({chartData.length} points)</div>
          </div>
        ) : (
          <div className="h-64 bg-slate-100 rounded-lg flex items-center justify-center">
            <div className="text-slate-400">No chart data available</div>
          </div>
        )}
      </div>

      {/* Recent Events */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          Recent Events
        </h2>
        {loadingEvents ? (
          <div className="space-y-3 animate-pulse">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-10 bg-slate-200 rounded"></div>
            ))}
          </div>
        ) : recentEvents.length > 0 ? (
          <DataTable
            columns={[
              { label: "Time", key: "timestamp" },
              { label: "Agent", key: "agentHostname" },
              { label: "File", key: "filePath" },
              {
                label: "Decision",
                key: "decision",
                render: (value) => <DecisionBadge decision={value} />,
              },
              {
                label: "User Action",
                key: "userAction",
                render: (value) =>
                  value ? (
                    <span className="text-slate-700">{value}</span>
                  ) : (
                    <span className="text-slate-400">—</span>
                  ),
              },
            ]}
            data={recentEvents}
            rowKey="id"
          />
        ) : (
          <div className="text-center py-8 text-slate-500">
            No recent events found
          </div>
        )}
      </div>
    </div>
  );
}
