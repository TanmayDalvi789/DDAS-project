/**
 * Custom React hooks for API data fetching
 * Handles loading, error, and data states
 */

"use client";

import { useEffect, useState } from "react";
import {
  getDashboardOverview,
  getAgents,
  getEvents,
  getEventDetail,
  getSettings,
  getCurrentUser,
  EventFilters,
  ApiResponse,
  ApiErrorResponse,
} from "./apiClient";
import { Agent, Event, EventDetail, Settings } from "./types";

export interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: ApiErrorResponse | null;
  refetch: () => void;
}

/**
 * Generic hook for fetching data from API
 */
function useApi<T>(
  fetchFn: () => Promise<ApiResponse<T>>,
  dependencies: any[] = []
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiErrorResponse | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchFn();
      setData(response.data);
      setError(response.error);
    } catch (err) {
      setError({
        status: 500,
        error: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, dependencies);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
  };
}

/**
 * Hook for dashboard overview data
 */
export function useDashboardOverview(): UseApiState<any> {
  return useApi(() => getDashboardOverview());
}

/**
 * Hook for agents list
 */
export function useAgents(): UseApiState<Agent[]> {
  return useApi(() => getAgents());
}

/**
 * Hook for events with filters
 */
export function useEvents(filters?: EventFilters): UseApiState<any> {
  return useApi(() => getEvents(filters), [
    filters?.agentId,
    filters?.decision,
    filters?.userAction,
    filters?.page,
    filters?.limit,
  ]);
}

/**
 * Hook for single event detail
 */
export function useEventDetail(eventId: string): UseApiState<EventDetail> {
  return useApi(() => getEventDetail(eventId), [eventId]);
}

/**
 * Hook for settings (admin only)
 */
export function useSettings(): UseApiState<Settings> {
  return useApi(() => getSettings());
}

/**
 * Hook for current user info
 */
export function useCurrentUser(): UseApiState<any> {
  return useApi(() => getCurrentUser());
}
