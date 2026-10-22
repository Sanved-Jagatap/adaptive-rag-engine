import Link from "next/link";
import { EvaluationDashboard } from "@/components/EvaluationDashboard";

export default function EvaluationPage() {
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="app-sidebar-logo">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500 text-white">
              <span className="text-sm font-semibold">
                AR
              </span>
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

          <Link href="/" className="nav-item">
            <span className="nav-icon">⌕</span>
            <span>Query console</span>
          </Link>

          <Link
            href="/evaluation"
            className="nav-item nav-item-active"
          >
            <span className="nav-icon">◫</span>
            <span>Evaluation</span>
          </Link>

          <div className="mt-7 mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
            System
          </div>

          <div className="nav-item cursor-default">
            <span className="nav-icon">◈</span>
            <span>Retrieval engine</span>
          </div>

          <div className="nav-item cursor-default">
            <span className="nav-icon">◇</span>
            <span>Evidence index</span>
          </div>

          <div className="nav-item cursor-default">
            <span className="nav-icon">◎</span>
            <span>Observability</span>
          </div>
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

      <div className="app-main">
        <header className="app-topbar">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span>Workspace</span>
            <span className="text-slate-300">/</span>
            <span className="font-medium text-slate-700">
              Evaluation
            </span>
          </div>

          <div className="status-pill">
            <span className="status-dot" />
            Evaluation data available
          </div>
        </header>

        <main className="app-content">
          <div className="mx-auto max-w-[1180px]">
            <div className="mb-8 flex items-end justify-between gap-6">
              <div>
                <div className="page-eyebrow">
                  Engineering analytics
                </div>

                <h1 className="page-title">
                  Evaluation dashboard
                </h1>

                <p className="page-description max-w-2xl">
                  Inspect retrieval performance, grounding
                  quality, category-level behavior, and
                  end-to-end latency.
                </p>
              </div>

              <Link
                href="/"
                className="hidden text-xs font-medium text-indigo-600 hover:text-indigo-700 sm:block"
              >
                ← Query console
              </Link>
            </div>

            <EvaluationDashboard />
          </div>
        </main>
      </div>
    </div>
  );
}