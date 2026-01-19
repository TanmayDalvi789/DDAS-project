/**
 * Agents Page
 * List of all agents with status
 */

"use client";

import { useState } from "react";
import { DataTable } from "../components/DataTable";
import { DecisionBadge } from "../components/DecisionBadge";
import { SectionHeader } from "../components/SectionHeader";
import { ErrorBanner } from "../components/ErrorBanner";
import { TableSkeleton } from "../components/SkeletonLoader";
import { useAgents } from "../lib/hooks";

function formatHeartbeat(isoTimestamp: string): string {
  const now = new Date();
  const timestamp = new Date(isoTimestamp);
  const diffMs = now.getTime() - timestamp.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  const timeStr = timestamp.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  let relativeStr = "";
  if (diffMins < 1) {
    relativeStr = "now";
  } else if (diffMins < 60) {
    relativeStr = `${diffMins} min ago`;
  } else if (diffHours < 24) {
    relativeStr = `${diffHours} hr ago`;
  } else {
    relativeStr = `${diffDays} day ago`;
  }

  return `${timeStr} (${relativeStr})`;
}

export default function AgentsPage() {
  const [dismissError, setDismissError] = useState(false);
  const { data: agents = [], loading, error } = useAgents();

  return (
    <div>
      <SectionHeader
        title="Agents"
        subtitle="Deployed agents and their current status"
      />

      {/* Error Banner */}
      {error && !dismissError && (
        <ErrorBanner 
          error={error} 
          onDismiss={() => setDismissError(true)}
        />
      )}

      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        {loading ? (
          <TableSkeleton />
        ) : agents && agents.length > 0 ? (
          <DataTable
            columns={[
              { label: "Agent ID", key: "id" },
              { label: "Hostname", key: "hostname" },
              { label: "OS", key: "os" },
              {
                label: "Last Heartbeat",
                key: "lastHeartbeat",
                render: (value) => (
                  <span title={value}>{formatHeartbeat(value)}</span>
                ),
              },
              {
                label: "Status",
                key: "status",
                render: (value) => <DecisionBadge decision={value} size="sm" />,
              },
            ]}
            data={agents}
            rowKey="id"
          />
        ) : (
          <div className="text-center py-8 text-slate-500">
            No agents found
          </div>
        )}
      </div>
    </div>
  );
}
