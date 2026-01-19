/**
 * Root Layout
 * Shared layout for dashboard pages with sidebar
 */

import type { Metadata } from "next";
import { LayoutContent } from "./components/LayoutContent";
import "./globals.css";

export const metadata: Metadata = {
  title: "DDAS Dashboard",
  description: "Distributed Duplicate Asset Scanner",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 m-0 p-0">
        <LayoutContent>{children}</LayoutContent>
      </body>
    </html>
  );
}
