/**
 * Event Detail Page
 * Detailed view of a single event
 */

"use client";

import { useState } from "react";
import { DecisionBadge } from "../../components/DecisionBadge";
import { SectionHeader } from "../../components/SectionHeader";
import { ErrorBanner } from "../../components/ErrorBanner";
import { CardSkeleton } from "../../components/SkeletonLoader";
import { useEventDetail } from "../../lib/hooks";
import { updateEventAction } from "../../lib/apiClient";

interface EventDetailPageProps {
  params: {
    eventId: string;
  };
}

export default function EventDetailPage({ params }: EventDetailPageProps) {
  const [dismissError, setDismissError] = useState(false);
  const [updatingAction, setUpdatingAction] = useState(false);
  const [actionMessage, setActionMessage] = useState("");

  const { data: event, loading, error, refetch } = useEventDetail(params.eventId);

  const handleApprove = async () => {
    setUpdatingAction(true);
    try {
      const response = await updateEventAction(params.eventId, "approved", "Approved by user");
      if (!response.error) {
        setActionMessage("Event approved successfully");
        refetch();
        setTimeout(() => setActionMessage(""), 3000);
      }
    } finally {
      setUpdatingAction(false);
    }
  };

  const handleDeny = async () => {
    setUpdatingAction(true);
    try {
      const response = await updateEventAction(params.eventId, "denied", "Denied by user");
      if (!response.error) {
        setActionMessage("Event denied successfully");
        refetch();
        setTimeout(() => setActionMessage(""), 3000);
      }
    } finally {
      setUpdatingAction(false);
    }
  };

  if (loading) {
    return (
      <div>
        <SectionHeader
          title={`Event ${params.eventId}`}
          subtitle="Detailed event information and detection signals"
        />
        <CardSkeleton />
      </div>
    );
  }

  if (error || !event) {
    return (
      <div>
        <SectionHeader
          title={`Event ${params.eventId}`}
          subtitle="Detailed event information and detection signals"
        />
        {error && !dismissError && (
          <ErrorBanner 
            error={error} 
            onDismiss={() => setDismissError(true)}
          />
        )}
        <div className="text-center py-8 text-slate-500">
          Event not found
        </div>
      </div>
    );
  }

  return (
    <div>
      <SectionHeader
        title={`Event ${event.id}`}
        subtitle="Detailed event information and detection signals"
      />

      {error && !dismissError && (
        <ErrorBanner 
          error={error} 
          onDismiss={() => setDismissError(true)}
        />
      )}

      <div className="space-y-6">
        {/* File Metadata */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            File Metadata
          </h2>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <div className="text-sm text-slate-500 mb-1">File Path</div>
              <div className="text-slate-900 font-mono text-sm">
                {event.filePath}
              </div>
            </div>
            <div>
              <div className="text-sm text-slate-500 mb-1">File Hash</div>
              <div className="text-slate-900 font-mono text-sm">
                {event.fileHash}
              </div>
            </div>
            <div>
              <div className="text-sm text-slate-500 mb-1">Size</div>
              <div className="text-slate-900">
                {(event.fileSize / 1024 / 1024).toFixed(2)} MB
              </div>
            </div>
            <div>
              <div className="text-sm text-slate-500 mb-1">Modified</div>
              <div className="text-slate-900">{event.fileModified}</div>
            </div>
            <div>
              <div className="text-sm text-slate-500 mb-1">Owner</div>
              <div className="text-slate-900">{event.owner}</div>
            </div>
            <div>
              <div className="text-sm text-slate-500 mb-1">Permissions</div>
              <div className="text-slate-900">{event.permissions}</div>
            </div>
          </div>
        </div>

        {/* Detection Signals */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Detection Signals ({event.signalCount})
          </h2>
          <div className="space-y-4">
            {event.signals.length > 0 ? (
              event.signals.map((signal, idx) => (
                <div key={idx} className="border border-slate-200 rounded-lg p-4 bg-slate-50">
                  <div className="flex items-start justify-between mb-2">
                    <div className="font-medium text-slate-900">
                      {signal.type.toUpperCase()} Match
                    </div>
                    <div className="text-sm text-slate-500">
                      {(signal.confidence * 100).toFixed(0)}% confidence
                    </div>
                  </div>
                  <div className="text-sm text-slate-700">{signal.details}</div>
                </div>
              ))
            ) : (
              <div className="text-slate-400">No signals detected</div>
            )}
          </div>
        </div>

        {/* Final Decision */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Final Decision
          </h2>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <div className="text-sm text-slate-500 mb-2">Decision</div>
              <DecisionBadge decision={event.decision} />
            </div>
            <div>
              <div className="text-sm text-slate-500 mb-1">Risk Score</div>
              <div className="text-slate-900 font-semibold">
                {(event.riskScore * 100).toFixed(0)}%
              </div>
            </div>
            <div>
              <div className="text-sm text-slate-500 mb-1">Timestamp</div>
              <div className="text-slate-700">{event.timestamp}</div>
            </div>
            <div>
              <div className="text-sm text-slate-500 mb-1">Backend Reference</div>
              <div className="text-slate-700 font-mono text-sm">
                {event.backendReference}
              </div>
            </div>
          </div>
        </div>

        {/* User Action */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            User Action
          </h2>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <div className="text-sm text-slate-500 mb-1">Status</div>
              <div className="text-slate-700 capitalize">
                {event.userAction || "Pending"}
              </div>
            </div>
            {event.userActionTimestamp && (
              <div>
                <div className="text-sm text-slate-500 mb-1">Timestamp</div>
                <div className="text-slate-700">{event.userActionTimestamp}</div>
              </div>
            )}
            {event.userActionReason && (
              <div className="col-span-2">
                <div className="text-sm text-slate-500 mb-1">Reason</div>
                <div className="text-slate-700">{event.userActionReason}</div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          {!event.userAction && (
            <div className="mt-6 pt-6 border-t border-slate-200 flex gap-3">
              <button
                onClick={handleApprove}
                disabled={updatingAction}
                className="btn-primary"
              >
                {updatingAction ? "Processing..." : "Approve"}
              </button>
              <button
                onClick={handleDeny}
                disabled={updatingAction}
                className="btn-secondary"
              >
                {updatingAction ? "Processing..." : "Deny"}
              </button>
            </div>
          )}
        </div>

        {/* Action Message */}
        {actionMessage && (
          <div className="success-message">
            {actionMessage}
          </div>
        )}

        {/* Agent Info */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">
            Agent Information
          </h2>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <div className="text-sm text-slate-500 mb-1">Agent ID</div>
              <div className="text-slate-700 font-mono text-sm">
                {event.agentId}
              </div>
            </div>
            <div>
              <div className="text-sm text-slate-500 mb-1">Hostname</div>
              <div className="text-slate-700">{event.agentHostname}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
