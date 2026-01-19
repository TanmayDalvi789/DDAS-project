/**
 * Centralized API Client for DDAS Dashboard
 * Handles authentication, error handling, and request/response formatting
 */

import { Agent, Event, EventDetail, Settings } from "./types";

export interface ApiErrorResponse {
  error?: string;
  message?: string;
  detail?: string;
  status: number;
}

export interface ApiResponse<T> {
  data: T | null;
  error: ApiErrorResponse | null;
  loading: boolean;
}

export interface PaginationParams {
  page?: number;
  limit?: number;
}

export interface EventFilters {
  agentId?: string;
  decision?: "ALLOW" | "WARN" | "BLOCK";
  userAction?: "approved" | "denied" | "pending";
  page?: number;
  limit?: number;
}

/**
 * Store JWT token in localStorage
 */
export function setAuthToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("auth_token", token);
  }
}

/**
 * Retrieve JWT token from localStorage
 */
export function getAuthToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("auth_token");
  }
  return null;
}

/**
 * Clear authentication token (logout)
 */
export function clearAuthToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("auth_token");
  }
}

/**
 * API client class with automatic JWT attachment and error handling
 */
class APIClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8001";
  }

  /**
   * Build request headers with Authorization token
   */
  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    const token = getAuthToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    return headers;
  }

  /**
   * Handle API errors globally
   */
  private async handleError(response: Response): Promise<ApiErrorResponse> {
    let errorData: ApiErrorResponse = {
      status: response.status,
    };

    try {
      const body = await response.json();
      errorData = {
        ...errorData,
        error: body.error || body.message || body.detail,
        message: body.message || body.detail,
      };
    } catch {
      errorData.error = `HTTP ${response.status}: ${response.statusText}`;
    }

    // Handle 401 Unauthorized - redirect to login
    if (response.status === 401) {
      clearAuthToken();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }

    // Handle 403 Forbidden
    if (response.status === 403) {
      errorData.error = "Access denied. You don't have permission to perform this action.";
    }

    return errorData;
  }

  /**
   * Make GET request
   */
  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: "GET",
        headers: this.getHeaders(),
      });

      if (!response.ok) {
        const error = await this.handleError(response);
        return { data: null, error, loading: false };
      }

      const data = await response.json();
      return { data, error: null, loading: false };
    } catch (err) {
      const error: ApiErrorResponse = {
        status: 500,
        error: err instanceof Error ? err.message : "Unknown error occurred",
      };
      return { data: null, error, loading: false };
    }
  }

  /**
   * Make POST request
   */
  async post<T>(endpoint: string, payload: Record<string, any>): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: "POST",
        headers: this.getHeaders(),
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await this.handleError(response);
        return { data: null, error, loading: false };
      }

      const data = await response.json();
      return { data, error: null, loading: false };
    } catch (err) {
      const error: ApiErrorResponse = {
        status: 500,
        error: err instanceof Error ? err.message : "Unknown error occurred",
      };
      return { data: null, error, loading: false };
    }
  }

  /**
   * Make PUT request
   */
  async put<T>(endpoint: string, payload: Record<string, any>): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: "PUT",
        headers: this.getHeaders(),
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const error = await this.handleError(response);
        return { data: null, error, loading: false };
      }

      const data = await response.json();
      return { data, error: null, loading: false };
    } catch (err) {
      const error: ApiErrorResponse = {
        status: 500,
        error: err instanceof Error ? err.message : "Unknown error occurred",
      };
      return { data: null, error, loading: false };
    }
  }
}

// Export singleton instance
export const apiClient = new APIClient();

// ============================================================================
// DASHBOARD API METHODS
// ============================================================================

/**
 * Get dashboard overview stats
 * GET /api/v1/dashboard/overview
 */
export async function getDashboardOverview(): Promise<ApiResponse<any>> {
  return apiClient.get("/api/v1/dashboard/overview");
}

/**
 * Get all agents for current organization
 * GET /api/v1/agents
 */
export async function getAgents(): Promise<ApiResponse<Agent[]>> {
  return apiClient.get("/api/v1/agents");
}

/**
 * Get single agent by ID
 * GET /api/v1/agents/:agentId
 */
export async function getAgent(agentId: string): Promise<ApiResponse<Agent>> {
  return apiClient.get(`/api/v1/agents/${agentId}`);
}

/**
 * Get events with optional filters and pagination
 * GET /api/v1/events?page=1&limit=10&agent_id=...&decision=...&user_action=...
 */
export async function getEvents(filters?: EventFilters): Promise<ApiResponse<any>> {
  const params = new URLSearchParams();

  if (filters?.agentId) params.append("agent_id", filters.agentId);
  if (filters?.decision) params.append("decision", filters.decision);
  if (filters?.userAction) params.append("user_action", filters.userAction);
  if (filters?.page) params.append("page", String(filters.page));
  if (filters?.limit) params.append("limit", String(filters.limit));

  const query = params.toString();
  const endpoint = query ? `/api/v1/events?${query}` : "/api/v1/events";

  return apiClient.get(endpoint);
}

/**
 * Get single event detail by ID
 * GET /api/v1/events/:eventId
 */
export async function getEventDetail(eventId: string): Promise<ApiResponse<EventDetail>> {
  return apiClient.get(`/api/v1/events/${eventId}`);
}

/**
 * Get settings (admin only)
 * GET /api/v1/settings
 */
export async function getSettings(): Promise<ApiResponse<Settings>> {
  return apiClient.get("/api/v1/settings");
}

/**
 * Update settings (admin only)
 * POST /api/v1/settings
 */
export async function updateSettings(settings: Partial<Settings>): Promise<ApiResponse<Settings>> {
  return apiClient.post("/api/v1/settings", settings);
}

/**
 * Authenticate user and get JWT token
 * POST /api/v1/auth/login
 */
export async function loginUser(email: string, password: string): Promise<ApiResponse<any>> {
  const response = await apiClient.post("/api/v1/auth/login", { email, password });
  if (response.data && (response.data as any).access_token) {
    setAuthToken((response.data as any).access_token);
  }
  return response;
}

/**
 * Logout user
 */
export async function logoutUser(): Promise<void> {
  clearAuthToken();
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

/**
 * Get current user info
 * GET /api/v1/auth/me
 */
export async function getCurrentUser(): Promise<ApiResponse<any>> {
  return apiClient.get("/api/v1/auth/me");
}

/**
 * Update user action on event (approve/deny)
 * POST /api/v1/events/:eventId/action
 */
export async function updateEventAction(
  eventId: string,
  action: "approved" | "denied",
  reason?: string
): Promise<ApiResponse<any>> {
  return apiClient.post(`/api/v1/events/${eventId}/action`, {
    action,
    reason: reason || "",
  });
}
