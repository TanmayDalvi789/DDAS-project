/**
 * Type definitions for DDAS Dashboard
 * Matches backend API contracts
 */

export interface Agent {
  id: string;
  hostname: string;
  os: string;
  lastHeartbeat: string;
  status: "RUNNING" | "OFFLINE" | "DEGRADED";
  version: string;
  organization_id: string;
}

export interface Event {
  id: string;
  agentId: string;
  agentHostname: string;
  timestamp: string;
  filePath: string;
  fileHash: string;
  decision: "ALLOW" | "WARN" | "BLOCK";
  userAction?: "approved" | "denied" | "pending";
  signals: DetectionSignal[];
}

export interface DetectionSignal {
  type: "fuzzy" | "semantic" | "exact";
  confidence: number;
  details: string;
}

export interface EventDetail extends Event {
  fileSize: number;
  fileModified: string;
  owner: string;
  permissions: string;
  signalCount: number;
  riskScore: number;
  backendReference: string;
  userActionTimestamp?: string;
  userActionReason?: string;
}

export interface StatCard {
  label: string;
  value: number | string;
  trend?: number;
  trendLabel?: string;
}

export interface Organization {
  id: string;
  name: string;
  createdAt: string;
}

export interface Settings {
  fuzzyThreshold: number;
  semanticThreshold: number;
  blockThreshold: number;
  warnThreshold: number;
  maxEventsPerDay: number;
}
