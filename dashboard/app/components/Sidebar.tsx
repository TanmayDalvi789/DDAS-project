/**
 * Sidebar Component
 * Left-side navigation for dashboard pages
 */

"use client";

import Link from "next/link";

export function Sidebar() {
  return (
    <aside className="w-60 flex-shrink-0 h-screen bg-slate-900 border-r border-slate-800 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between h-16 px-6 border-b border-slate-800">
        <div className="text-lg font-semibold text-white">DDAS</div>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 p-4 flex-1">
        <Link href="/">
          <div className="nav-link">Overview</div>
        </Link>
        <Link href="/agents">
          <div className="nav-link">Agents</div>
        </Link>
        <Link href="/events">
          <div className="nav-link">Events</div>
        </Link>
        <Link href="/settings">
          <div className="nav-link">Settings</div>
        </Link>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-slate-800">
        <div className="text-xs text-slate-400">
          DDAS Console
        </div>
      </div>
    </aside>
  );
}

