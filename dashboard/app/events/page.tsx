/**
 * Events Page
 * Paginated list of all events with filtering
 */

"use client";

import { useState } from "react";
import { DataTable } from "../components/DataTable";
import { DecisionBadge } from "../components/DecisionBadge";
import { SectionHeader } from "../components/SectionHeader";
import { ErrorBanner } from "../components/ErrorBanner";
import { TableSkeleton } from "../components/SkeletonLoader";
import { useEvents } from "../lib/hooks";

export default function EventsPage() {
  const [dismissError, setDismissError] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [agentFilter, setAgentFilter] = useState("");
  const [decisionFilter, setDecisionFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("");

  const itemsPerPage = 10;

  // Build filters object
  const filters = {
    page: currentPage,
    limit: itemsPerPage,
    ...(agentFilter && { agentId: agentFilter }),
    ...(decisionFilter && { decision: decisionFilter as any }),
    ...(actionFilter && { userAction: actionFilter as any }),
  };

  const { data: eventsResponse, loading, error } = useEvents(filters);

  // Extract pagination info from API response
  const events = eventsResponse?.events || [];
  const totalEvents = eventsResponse?.total || 0;
  const totalPages = Math.ceil(totalEvents / itemsPerPage);

  return (
    <div>
      <SectionHeader
        title="Events"
        subtitle="All detected file events across agents"
      />

      {/* Error Banner */}
      {error && !dismissError && (
        <ErrorBanner 
          error={error} 
          onDismiss={() => setDismissError(true)}
        />
      )}

      {/* Filter Row */}
      <div className="bg-slate-50 px-4 py-4 mb-6 rounded-lg">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Agent
            </label>
            <select 
              className="select-field"
              value={agentFilter}
              onChange={(e) => {
                setAgentFilter(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="">All Agents</option>
              {/* Agent options would be populated from useAgents hook */}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Decision
            </label>
            <select 
              className="select-field"
              value={decisionFilter}
              onChange={(e) => {
                setDecisionFilter(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="">All Decisions</option>
              <option value="ALLOW">ALLOW</option>
              <option value="WARN">WARN</option>
              <option value="BLOCK">BLOCK</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              User Action
            </label>
            <select 
              className="select-field"
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="">All Actions</option>
              <option value="approved">Approved</option>
              <option value="denied">Denied</option>
              <option value="pending">Pending</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              &nbsp;
            </label>
            <button className="w-full btn-neutral btn-sm">
              Search
            </button>
          </div>
        </div>
      </div>

      {/* Events Table */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 mb-6 shadow-sm">
        {loading ? (
          <TableSkeleton />
        ) : events.length > 0 ? (
          <DataTable
            columns={[
              { label: "Time", key: "timestamp" },
              { label: "Agent", key: "agentHostname" },
              { label: "File", key: "filePath" },
              {
                label: "Decision",
                key: "decision",
                render: (value) => <DecisionBadge decision={value} size="sm" />,
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
            data={events}
            rowKey="id"
          />
        ) : (
          <div className="text-center py-8 text-slate-500">
            No events found
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-slate-600">
          {events.length > 0 ? (
            <>
              Showing {(currentPage - 1) * itemsPerPage + 1} to{" "}
              {Math.min(currentPage * itemsPerPage, totalEvents)} of {totalEvents} events
            </>
          ) : (
            "No events to display"
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className="btn-secondary btn-sm"
          >
            Previous
          </button>
          <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const pageNum = i + 1;
              return (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`px-3 py-2 rounded-lg transition-all duration-200 ${
                    currentPage === pageNum
                      ? "btn-primary btn-sm"
                      : "btn-secondary btn-sm"
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
            {totalPages > 5 && <span className="text-slate-600 px-2">...</span>}
          </div>
          <button
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
            className="btn-secondary btn-sm"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
