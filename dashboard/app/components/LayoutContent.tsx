"use client";

import { Sidebar } from "./Sidebar";

export function LayoutContent({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto bg-slate-50">
        <div className="p-8">
          <div className="max-w-7xl mx-auto">{children}</div>
        </div>
      </main>
    </div>
  );
}
