/**
 * Settings Page
 * System configuration and downloads
 */

"use client";

import { useState, useEffect } from "react";
import { SectionHeader } from "../components/SectionHeader";
import { ErrorBanner } from "../components/ErrorBanner";
import { CardSkeleton } from "../components/SkeletonLoader";
import { useSettings } from "../lib/hooks";
import { updateSettings } from "../lib/apiClient";
import { Settings } from "../lib/types";

export default function SettingsPage() {
  const [dismissError, setDismissError] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const { data: settings, loading: loadingSettings, error: settingsError, refetch } = useSettings();
  const [editedSettings, setEditedSettings] = useState<Partial<Settings>>({});

  // Initialize edited settings when data loads
  useEffect(() => {
    if (settings) {
      setEditedSettings(settings);
    }
  }, [settings]);

  const handleChange = (key: keyof Settings, value: number) => {
    setEditedSettings({
      ...editedSettings,
      [key]: value,
    });
    setSaved(false);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await updateSettings(editedSettings);
      if (response.error) {
        // Error is displayed by ErrorBanner
      } else {
        setSaved(true);
        refetch();
        setTimeout(() => setSaved(false), 3000);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDownloadProxy = async () => {
    setDownloading(true);
    try {
      const response = await fetch("http://localhost:8001/api/v1/downloads/proxy/windows");
      if (!response.ok) {
        throw new Error("Failed to download proxy");
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "ddas_proxy.exe";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Download failed:", error);
      alert("Failed to download proxy executable");
    } finally {
      setDownloading(false);
    }
  };

  const validateInput = (value: string, min: number, max: number): number => {
    const num = parseFloat(value);
    if (isNaN(num)) return min;
    return Math.min(Math.max(num, min), max);
  };

  return (
    <div>
      <SectionHeader
        title="Settings"
        subtitle="System configuration and downloads"
      />

      {/* Error Banner */}
      {settingsError && !dismissError && (
        <ErrorBanner 
          error={settingsError!} 
          onDismiss={() => setDismissError(true)}
        />
      )}

      {loadingSettings ? (
        <CardSkeleton />
      ) : (
        <div className="space-y-6">
          {/* Proxy Download Section */}
          <div className="bg-white border border-slate-200 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">
              Proxy Executable
            </h2>
            <p className="text-sm text-slate-600 mb-4">
              Download the DDAS Proxy executable for Windows deployment
            </p>
            <button
              onClick={handleDownloadProxy}
              disabled={downloading}
              className="btn-primary"
            >
              {downloading ? "Downloading..." : "Download Proxy (Windows)"}
            </button>
          </div>

          {/* Divider */}
          <div className="divider"></div>

          {/* Detection Thresholds */}
          <div className="bg-white border border-slate-200 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-6">
              Detection Thresholds
            </h2>
            <div className="space-y-6">
              {/* Fuzzy Threshold */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Fuzzy Match Threshold
                </label>
                <input
                  type="number"
                  min="0.0"
                  max="1.0"
                  step="0.01"
                  value={editedSettings.fuzzyThreshold?.toFixed(2) || "0.0"}
                  onChange={(e) =>
                    handleChange(
                      "fuzzyThreshold",
                      validateInput(e.target.value, 0, 1)
                    )
                  }
                  className="input-numeric"
                  disabled={saving}
                />
                <p className="text-xs text-slate-500 mt-1">
                  Files matching this threshold will trigger fuzzy detection (0.0–1.0)
                </p>
              </div>

              {/* Semantic Threshold */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Semantic Search Threshold
                </label>
                <input
                  type="number"
                  min="0.0"
                  max="1.0"
                  step="0.01"
                  value={editedSettings.semanticThreshold?.toFixed(2) || "0.0"}
                  onChange={(e) =>
                    handleChange(
                      "semanticThreshold",
                      validateInput(e.target.value, 0, 1)
                    )
                  }
                  className="input-numeric"
                  disabled={saving}
                />
                <p className="text-xs text-slate-500 mt-1">
                  Files matching this threshold will be flagged by semantic search (0.0–1.0)
                </p>
              </div>

              {/* Block Threshold */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Block Decision Threshold
                </label>
                <input
                  type="number"
                  min="0.0"
                  max="1.0"
                  step="0.01"
                  value={editedSettings.blockThreshold?.toFixed(2) || "0.0"}
                  onChange={(e) =>
                    handleChange(
                      "blockThreshold",
                      validateInput(e.target.value, 0, 1)
                    )
                  }
                  className="input-numeric"
                  disabled={saving}
                />
                <p className="text-xs text-slate-500 mt-1">
                  Risk scores above this will result in BLOCK decision (0.0–1.0)
                </p>
              </div>

              {/* Warn Threshold */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Warning Decision Threshold
                </label>
                <input
                  type="number"
                  min="0.0"
                  max="1.0"
                  step="0.01"
                  value={editedSettings.warnThreshold?.toFixed(2) || "0.0"}
                  onChange={(e) =>
                    handleChange(
                      "warnThreshold",
                      validateInput(e.target.value, 0, 1)
                    )
                  }
                  className="input-numeric"
                  disabled={saving}
                />
                <p className="text-xs text-slate-500 mt-1">
                  Risk scores above this will result in WARN decision (0.0–1.0)
                </p>
              </div>
            </div>
          </div>

          {/* Divider */}
          <div className="divider"></div>

          {/* Rate Limiting */}
          <div className="bg-white border border-slate-200 rounded-xl p-6">
            <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-6">
              System Safeguards
            </h3>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">
                Max Events Per Day
              </label>
              <input
                type="number"
                value={editedSettings.maxEventsPerDay || 0}
                onChange={(e) =>
                  handleChange("maxEventsPerDay", parseInt(e.target.value))
                }
                className="input-numeric"
                disabled={saving}
              />
              <p className="text-xs text-slate-500 mt-1">
                Maximum events processed per organization per day
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn-primary"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
            <button className="btn-secondary">
              Reset to Defaults
            </button>
          </div>

          {/* Save Confirmation */}
          {saved && (
            <div className="success-message">
              Settings saved successfully
            </div>
          )}

          {/* Safety Note */}
          <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 mt-8">
            <p className="text-xs text-slate-600">
              Changes apply to future events only. Existing decisions are not affected.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
