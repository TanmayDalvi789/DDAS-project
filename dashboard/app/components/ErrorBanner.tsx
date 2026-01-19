/**
 * ErrorBanner Component
 * Displays API errors to the user
 */

import { ApiErrorResponse } from "../lib/apiClient";

interface ErrorBannerProps {
  error: ApiErrorResponse;
  onDismiss?: () => void;
}

export function ErrorBanner({ error, onDismiss }: ErrorBannerProps) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold text-red-900 mb-1">Error</h3>
          <p className="text-sm text-red-700">
            {error.error || error.message || "An error occurred"}
          </p>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-red-500 hover:text-red-700 transition-colors"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}
