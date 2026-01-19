/**
 * Centralized mock data for DDAS Dashboard
 * Used for UI scaffolding; replace with API calls in implementation
 */

import {
  Agent,
  Event,
  EventDetail,
  DetectionSignal,
  Settings,
} from "./types";

export const mockStats = {
  activeAgents: 12,
  totalEvents: 5432,
  warnCount: 234,
  blockCount: 18,
};

export const mockAgents: Agent[] = [
  {
    id: "agent-001",
    hostname: "workstation-01.company.local",
    os: "Windows 10",
    lastHeartbeat: "2026-01-17T14:32:00Z",
    status: "RUNNING",
    version: "0.2.0",
    organization_id: "org-001",
  },
  {
    id: "agent-002",
    hostname: "laptop-03.company.local",
    os: "macOS 14.2",
    lastHeartbeat: "2026-01-17T14:28:00Z",
    status: "RUNNING",
    version: "0.2.0",
    organization_id: "org-001",
  },
  {
    id: "agent-003",
    hostname: "server-build.company.local",
    os: "Ubuntu 22.04",
    lastHeartbeat: "2026-01-16T08:15:00Z",
    status: "OFFLINE",
    version: "0.1.9",
    organization_id: "org-001",
  },
  {
    id: "agent-004",
    hostname: "workstation-05.company.local",
    os: "Windows 11",
    lastHeartbeat: "2026-01-17T13:45:00Z",
    status: "RUNNING",
    version: "0.2.0",
    organization_id: "org-001",
  },
  {
    id: "agent-005",
    hostname: "dev-machine.company.local",
    os: "macOS 13.5",
    lastHeartbeat: "2026-01-17T10:22:00Z",
    status: "DEGRADED",
    version: "0.2.0",
    organization_id: "org-001",
  },
];

export const mockEvents: Event[] = [
  {
    id: "evt-5001",
    agentId: "agent-001",
    agentHostname: "workstation-01.company.local",
    timestamp: "2026-01-17T14:25:30Z",
    filePath: "C:\\Users\\john\\Downloads\\document.exe",
    fileHash: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    decision: "BLOCK",
    userAction: "pending",
    signals: [
      { type: "exact", confidence: 0.99, details: "Known malware signature" },
      { type: "fuzzy", confidence: 0.85, details: "Similar to quarantined file" },
    ],
  },
  {
    id: "evt-5000",
    agentId: "agent-002",
    agentHostname: "laptop-03.company.local",
    timestamp: "2026-01-17T14:22:15Z",
    filePath: "/Users/alice/Downloads/installer.dmg",
    fileHash: "q9w8e7r6t5y4u3i2o1p0a9s8d7f6g5h4",
    decision: "WARN",
    userAction: "approved",
    signals: [
      { type: "semantic", confidence: 0.72, details: "Suspicious behavior pattern" },
    ],
  },
  {
    id: "evt-4999",
    agentId: "agent-001",
    agentHostname: "workstation-01.company.local",
    timestamp: "2026-01-17T14:18:45Z",
    filePath: "C:\\Program Files\\Office\\winword.exe",
    fileHash: "m1n2o3p4q5r6s7t8u9v0w1x2y3z4a5b6",
    decision: "ALLOW",
    userAction: undefined,
    signals: [],
  },
  {
    id: "evt-4998",
    agentId: "agent-004",
    agentHostname: "workstation-05.company.local",
    timestamp: "2026-01-17T14:15:20Z",
    filePath: "C:\\temp\\setup.msi",
    fileHash: "z9y8x7w6v5u4t3s2r1q0p9o8n7m6l5k4",
    decision: "WARN",
    userAction: "denied",
    signals: [
      { type: "fuzzy", confidence: 0.68, details: "Partial match to known variant" },
    ],
  },
  {
    id: "evt-4997",
    agentId: "agent-002",
    agentHostname: "laptop-03.company.local",
    timestamp: "2026-01-17T14:12:00Z",
    filePath: "/home/bob/file.zip",
    fileHash: "h4g5f6e7d8c9b0a1z2y3x4w5v6u7t8s9",
    decision: "ALLOW",
    userAction: undefined,
    signals: [],
  },
];

export const mockEventDetail: EventDetail = {
  id: "evt-5001",
  agentId: "agent-001",
  agentHostname: "workstation-01.company.local",
  timestamp: "2026-01-17T14:25:30Z",
  filePath: "C:\\Users\\john\\Downloads\\document.exe",
  fileHash: "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  decision: "BLOCK",
  userAction: "pending",
  fileSize: 2048576,
  fileModified: "2026-01-17T10:12:00Z",
  owner: "john.doe",
  permissions: "rw-r--r--",
  signalCount: 2,
  riskScore: 0.95,
  backendReference: "sig-ref-8f7e6d5c",
  signals: [
    { type: "exact", confidence: 0.99, details: "Known malware signature" },
    { type: "fuzzy", confidence: 0.85, details: "Similar to quarantined file" },
  ],
};

export const mockSettings: Settings = {
  fuzzyThreshold: 0.70,
  semanticThreshold: 0.65,
  blockThreshold: 0.90,
  warnThreshold: 0.70,
  maxEventsPerDay: 10000,
};
