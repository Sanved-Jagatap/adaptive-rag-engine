"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SystemStatusProvider } from "./SystemStatusContext";

function Icon({
  children,
}: {
  children: React.ReactNode;
}) {
  return <span className="nav-icon">{children}</span>;
}

function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname === href;
  };

  return (
    <aside className="app-sidebar">
      <div className="app-sidebar-logo">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500 text-white shadow-lg shadow-indigo-950/20">
            <span className="text-sm font-semibold">AR</span>
          </div>

          <div>
            <div className="text-sm font-semibold tracking-tight">
              Adaptive RAG
            </div>
            <div className="mt-0.5 text-[11px] text-slate-400">
              Intelligence Engine
            </div>
          </div>
        </div>
      </div>

      <div className="app-sidebar-content">
        <div className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
          Workspace
        </div>

        <Link
          href="/"
          prefetch
          className={`nav-item ${isActive("/") ? "nav-item-active" : ""}`}
        >
          <Icon>⌕</Icon>
          <span>Query console</span>
        </Link>

        <Link
          href="/evaluation"
          prefetch
          className={`nav-item ${
            isActive("/evaluation") ? "nav-item-active" : ""
          }`}
        >
          <Icon>◫</Icon>
          <span>Evaluation</span>
        </Link>

        <div className="mt-7 mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
          System
        </div>

        <Link
          href="/system/retrieval"
          prefetch
          className={`nav-item ${
            isActive("/system/retrieval") ? "nav-item-active" : ""
          }`}
        >
          <Icon>◈</Icon>
          <span>Retrieval engine</span>
        </Link>

        <Link
          href="/system/index"
          prefetch
          className={`nav-item ${
            isActive("/system/index") ? "nav-item-active" : ""
          }`}
        >
          <Icon>◇</Icon>
          <span>Evidence index</span>
        </Link>

        <Link
          href="/system/observability"
          prefetch
          className={`nav-item ${
            isActive("/system/observability") ? "nav-item-active" : ""
          }`}
        >
          <Icon>◎</Icon>
          <span>Observability</span>
        </Link>
      </div>

      <div className="app-sidebar-footer">
        <div className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
          <div className="mb-2 flex items-center gap-2">
            <span className="status-dot" />
            <span className="text-xs font-medium text-slate-200">
              Engine operational
            </span>
          </div>

          <div className="font-mono text-[10px] text-slate-500">
            v0.6 · local inference
          </div>
        </div>
      </div>
    </aside>
  );
}

function Topbar() {
  const pathname = usePathname();

  const page =
    pathname === "/system/retrieval"
      ? "Retrieval Engine"
      : pathname === "/system/index"
        ? "Evidence Index"
        : pathname === "/system/observability"
          ? "Observability"
          : "System";

  return (
    <header className="app-topbar">
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <span>System</span>
        <span className="text-slate-300">/</span>
        <span className="font-medium text-slate-700">{page}</span>
      </div>

      <div className="status-pill">
        <span className="status-dot" />
        All systems operational
      </div>
    </header>
  );
}

export default function SystemLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SystemStatusProvider>
      <div className="app-shell">
        <Sidebar />

        <div className="app-main">
          <Topbar />
          <main className="app-content">{children}</main>
        </div>
      </div>
    </SystemStatusProvider>
  );
}
