"use client";

import { useEffect, useState, FormEvent } from "react";
import Link from "next/link";
import {
  runQuery,
  ApiError,
  type QueryResponse,
} from "@/lib/api";
import {
  loadHistory,
  saveHistoryEntry,
  clearHistory,
  type QueryHistoryEntry,
} from "@/lib/history";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { InfoTag } from "@/components/InfoTag";
import { SourceRow } from "@/components/SourceRow";
import { QueryHistoryPanel } from "@/components/QueryHistoryPanel";

function Icon({
  children,
}: {
  children: React.ReactNode;
}) {
  return <span className="nav-icon">{children}</span>;
}

function Sidebar() {
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

        <Link href="/" className="nav-item nav-item-active">
          <Icon>⌕</Icon>
          <span>Query console</span>
        </Link>

        <Link href="/evaluation" className="nav-item">
          <Icon>◫</Icon>
          <span>Evaluation</span>
        </Link>

        <div className="mt-7 mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
          System
        </div>

        <Link href="/system/retrieval" className="nav-item">
          <Icon>◈</Icon>
          <span>Retrieval engine</span>
        </Link>

        <Link href="/system/index" className="nav-item">
          <Icon>◇</Icon>
          <span>Evidence index</span>
        </Link>

        <Link href="/system/observability" className="nav-item">
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
  return (
    <header className="app-topbar">
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <span>Workspace</span>
        <span className="text-slate-300">/</span>
        <span className="font-medium text-slate-700">Query Console</span>
      </div>

      <div className="status-pill">
        <span className="status-dot" />
        All systems operational
      </div>
    </header>
  );
}

export function QueryConsole() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [history, setHistory] = useState<QueryHistoryEntry[]>([]);

  useEffect(() => {
    setHistory(loadHistory());
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    const trimmed = query.trim();

    if (!trimmed || loading) {
      return;
    }

    const recentContext =
      history.length > 0
        ? `User: ${history[0].query}\nAssistant: ${history[0].response.answer}`
        : "";

    setLoading(true);
    setError(null);

    try {
      const result = await runQuery(trimmed, 5, recentContext);

      setResponse(result);

      const entry: QueryHistoryEntry = {
        id: crypto.randomUUID(),
        query: trimmed,
        timestamp: Date.now(),
        response: result,
      };

      setHistory(saveHistoryEntry(entry));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Something went wrong running that query.",
      );

      setResponse(null);
    } finally {
      setLoading(false);
    }
  }

  function handleSelectHistory(entry: QueryHistoryEntry) {
    setQuery(entry.query);
    setResponse(entry.response);
    setError(null);
  }

  function handleClearHistory() {
    clearHistory();
    setHistory([]);
  }

  return (
    <div className="app-shell">
      <Sidebar />

      <div className="app-main">
        <Topbar />

        <main className="app-content">
          <div className="mx-auto max-w-[1180px]">
            {/* Page heading */}
            <div className="mb-8">
              <div className="page-eyebrow">
                Retrieval intelligence
              </div>

              <h1 className="page-title">
                Query your knowledge base
              </h1>

              <p className="page-description max-w-2xl">
                Ask technical questions and inspect how the engine routes,
                retrieves, reranks, and grounds each answer.
              </p>
            </div>

            {/* Query composer */}
            <section className="mb-7">
              <form onSubmit={handleSubmit}>
                <div className="query-composer">
                  <textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Ask a question about the indexed corpus..."
                    className="query-input"
                    aria-label="Query"
                    rows={2}
                    onKeyDown={(e) => {
                      if (
                        e.key === "Enter" &&
                        !e.shiftKey
                      ) {
                        e.preventDefault();

                        if (query.trim() && !loading) {
                          e.currentTarget.form?.requestSubmit();
                        }
                      }
                    }}
                  />

                  <div className="query-composer-footer">
                    <div className="flex items-center gap-2 text-[11px] text-slate-400">
                      <span className="font-mono">
                        ENTER
                      </span>
                      <span>to run</span>
                      <span className="text-slate-300">·</span>
                      <span>
                        SHIFT + ENTER for newline
                      </span>
                    </div>

                    <button
                      type="submit"
                      disabled={loading || !query.trim()}
                      className="primary-button"
                    >
                      {loading ? (
                        <>
                          <span className="h-3 w-3 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                          Retrieving
                        </>
                      ) : (
                        <>
                          Run query
                          <span aria-hidden="true">→</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </form>
            </section>

            {/* Recent queries */}
            {history.length > 0 && (
              <section className="mb-8">
                <div className="mb-3 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-semibold text-slate-700">
                      Recent queries
                    </div>
                    <div className="mt-0.5 text-[11px] text-slate-400">
                      Continue a previous investigation
                    </div>
                  </div>
                </div>

                <div className="ui-card overflow-hidden p-1 query-history-polished">
                  <QueryHistoryPanel
                    entries={history}
                    onSelect={handleSelectHistory}
                    onClear={handleClearHistory}
                  />
                </div>
              </section>
            )}

            {/* Error */}
            {error && (
              <div className="mb-7 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                <div className="font-medium">
                  Query failed
                </div>

                <div className="mt-1 text-xs text-red-600">
                  {error}
                </div>
              </div>
            )}

            {/* Empty state */}
            {!response &&
              !error &&
              !loading && (
                <div className="empty-state compact-empty-state">
                  <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-indigo-100 bg-indigo-50 text-indigo-600">
                    ◇
                  </div>

                  <h2 className="text-sm font-semibold text-slate-800">
                    Ready for your question
                  </h2>

                  <p className="mx-auto mt-2 max-w-md text-xs leading-5 text-slate-500">
                    The engine will select a retrieval strategy,
                    rank evidence, and generate a grounded answer
                    with source citations.
                  </p>
                </div>
              )}

            {/* Results */}
            {response && (
              <div
                key={`${response.used_query}-${response.answer}`}
                className="settle-in"
              >
                {/* Result header */}
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="text-xs font-semibold text-slate-700">
                      Query result
                    </div>

                    <div className="mt-1 max-w-3xl truncate font-mono text-[11px] text-slate-400">
                      {response.used_query}
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <ConfidenceBadge
                      level={response.confidence_level}
                    />

                    <InfoTag
                      label="strategy"
                      value={response.strategy}
                    />

                    <InfoTag
                      label="decided by"
                      value={response.decided_by.replace(
                        /_/g,
                        " ",
                      )}
                    />

                    {response.was_rewritten && (
                      <InfoTag
                        label="query"
                        value="rewritten"
                      />
                    )}
                  </div>
                </div>

                {response.invalid_citations.length > 0 && (
                  <div className="mb-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    <div className="font-medium">
                      {response.invalid_citations.length} invalid citation
                      {response.invalid_citations.length > 1 ? "s" : ""} detected and removed
                    </div>
                    <div className="mt-1 text-xs text-red-600">
                      Source
                      {response.invalid_citations.length > 1 ? "s" : ""} #
                      {response.invalid_citations.join(", #")}{" "}
                      {response.invalid_citations.length > 1 ? "were" : "was"}{" "}
                      not present in the retrieved evidence.
                    </div>
                  </div>
                )}

                {/* Main result grid */}
                <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.85fr)]">
                  {/* Answer */}
                  <section className="ui-card overflow-hidden self-start">
                    <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
                          Grounded answer
                        </div>

                        <div className="mt-1 text-[11px] text-slate-400">
                          Generated from retrieved evidence
                        </div>
                      </div>

                      <div className="status-pill">
                        <span className="status-dot" />
                        Evidence backed
                      </div>
                    </div>

                    <div className="px-5 py-6">
                      <p className="text-[15px] leading-7 text-slate-700">
                        {response.answer}
                      </p>
                    </div>

                    <div className="grid grid-cols-2 border-t border-slate-100">
                      <div className="border-r border-slate-100 px-5 py-4">
                        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                          CITATION VALIDITY
                        </div>

                        <div className="mt-1 font-mono text-lg text-slate-800">
                          {(
                            response.citation_coverage *
                            100
                          ).toFixed(0)}
                          %
                        </div>
                      </div>

                      <div className="px-5 py-4">
                        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                          Evidence status
                        </div>

                        <div className="mt-1 text-sm font-medium text-emerald-600">
                          {response.sufficient_evidence
                            ? "Sufficient"
                            : "Insufficient"}
                        </div>
                      </div>
                    </div>
                  </section>

                  {/* Sources */}
                  <section>
                    <div className="mb-3 flex items-end justify-between">
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
                          Evidence
                        </div>

                        <div className="mt-1 text-[11px] text-slate-400">
                          {response.sources.length} retrieved
                          sources
                        </div>
                      </div>

                      <div className="font-mono text-xs text-slate-500">
                        {(
                          response.citation_coverage *
                          100
                        ).toFixed(0)}
                        % valid
                      </div>
                    </div>

                    <ul className="space-y-2">
                      {response.sources.map(
                        (source, i) => (
                          <SourceRow
                            key={source.chunk_id}
                            source={source}
                            rank={i + 1}
                            isCited={response.cited_sources.includes(
                              i + 1,
                            )}
                          />
                        ),
                      )}

                      {response.sources.length === 0 && (
                        <li className="empty-state py-8">
                          <p className="text-xs text-slate-500">
                            No evidence was retrieved for
                            this query.
                          </p>
                        </li>
                      )}
                    </ul>
                  </section>
                </div>

                {/* Query intelligence */}
                <section className="mt-5">
                  <div className="mb-3">
                    <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
                      Query intelligence
                    </div>
                    <div className="mt-1 text-[11px] text-slate-400">
                      How the adaptive retrieval pipeline handled this query
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                    <div className="ui-card p-5">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-400">
                            Routing
                          </div>
                          <div className="mt-2 text-sm font-semibold text-slate-800">
                            {response.strategy.toUpperCase()}
                          </div>
                        </div>
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                          ↗
                        </div>
                      </div>
                      <div className="mt-4 border-t border-slate-100 pt-3">
                        <div className="text-[10px] uppercase tracking-wider text-slate-400">
                          Decision source
                        </div>
                        <div className="mt-1 text-xs font-medium text-slate-700">
                          {response.decided_by.replace(/_/g, " ")}
                        </div>
                      </div>
                    </div>

                    <div className="ui-card p-5">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-400">
                            Query processing
                          </div>
                          <div className="mt-2 text-sm font-semibold text-slate-800">
                            {response.was_rewritten ? "Contextual rewrite" : "Original query"}
                          </div>
                        </div>
                        <div
                          className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                            response.was_rewritten
                              ? "bg-indigo-50 text-indigo-600"
                              : "bg-slate-50 text-slate-500"
                          }`}
                        >
                          {response.was_rewritten ? "↻" : "—"}
                        </div>
                      </div>
                      <div className="mt-4 border-t border-slate-100 pt-3">
                        <div className="text-[10px] uppercase tracking-wider text-slate-400">
                          Used for retrieval
                        </div>
                        <div className="mt-1 truncate font-mono text-[11px] text-slate-600">
                          {response.used_query}
                        </div>
                      </div>
                    </div>

                    <div className="ui-card p-5">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-400">
                            Evidence
                          </div>
                          <div className="mt-2 text-sm font-semibold text-slate-800">
                            {response.sufficient_evidence ? "Grounded" : "Insufficient"}
                          </div>
                        </div>
                        <div
                          className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                            response.sufficient_evidence
                              ? "bg-emerald-50 text-emerald-600"
                              : "bg-amber-50 text-amber-600"
                          }`}
                        >
                          {response.sufficient_evidence ? "✓" : "!"}
                        </div>
                      </div>
                      <div className="mt-4 border-t border-slate-100 pt-3">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] uppercase tracking-wider text-slate-400">
                            Citation validity
                          </span>
                          <span className="font-mono text-xs font-medium text-slate-700">
                            {(response.citation_coverage * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
                          <div
                            className="h-full rounded-full bg-indigo-500 transition-all"
                            style={{
                              width: `${Math.min(
                                100,
                                Math.max(0, response.citation_coverage * 100),
                              )}%`,
                            }}
                          />
                        </div>

                          {response.invalid_citations.length > 0 && (
                            <div className="mt-3 flex items-center justify-between text-[11px]">
                              <span className="text-slate-400">
                                Invalid citations removed
                              </span>
                              <span className="font-mono font-medium text-red-600">
                                {response.invalid_citations.length}
                              </span>
                            </div>
                          )}
                      </div>
                    </div>
                  </div>
                </section>

                <section className="mt-5 ui-card overflow-hidden">
                  <div className="border-b border-slate-100 px-5 py-4">
                    <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
                      Retrieval pipeline
                    </div>
                    <div className="mt-1 text-[11px] text-slate-400">
                      Execution path selected for this request
                    </div>
                  </div>

                  <div className="grid grid-cols-1 divide-y divide-slate-100 md:grid-cols-4 md:divide-x md:divide-y-0">
                    <div className="p-5">
                      <div className="mb-3 flex items-center gap-2">
                        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-50 text-xs font-semibold text-indigo-600">
                          01
                        </span>
                        <span className="text-xs font-semibold text-slate-700">Route</span>
                      </div>
                      <div className="text-sm font-medium text-slate-800">
                        {response.strategy.toUpperCase()}
                      </div>
                      <div className="mt-1 text-[11px] leading-5 text-slate-400">
                        Adaptive strategy selected for the query.
                      </div>
                    </div>

                    <div className="p-5">
                      <div className="mb-3 flex items-center gap-2">
                        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 text-xs font-semibold text-slate-600">
                          02
                        </span>
                        <span className="text-xs font-semibold text-slate-700">Retrieve</span>
                      </div>
                      <div className="text-sm font-medium text-slate-800">
                        {response.sources.length} sources
                      </div>
                      <div className="mt-1 text-[11px] leading-5 text-slate-400">
                        Evidence retrieved from the indexed corpus.
                      </div>
                    </div>

                    <div className="p-5">
                      <div className="mb-3 flex items-center gap-2">
                        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100 text-xs font-semibold text-slate-600">
                          03
                        </span>
                        <span className="text-xs font-semibold text-slate-700">Rerank</span>
                      </div>
                      <div className="text-sm font-medium text-slate-800">
                        {response.sources.some((source) => source.rerank_score !== null)
                          ? "Cross-encoder"
                          : "Not applied"}
                      </div>
                      <div className="mt-1 text-[11px] leading-5 text-slate-400">
                        {response.sources.some((source) => source.rerank_score !== null)
                          ? "Retrieved evidence was assigned reranking scores."
                          : "No reranking score was returned for this request."}
                      </div>
                    </div>

                    <div className="p-5">
                      <div className="mb-3 flex items-center gap-2">
                        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-50 text-xs font-semibold text-emerald-600">
                          04
                        </span>
                        <span className="text-xs font-semibold text-slate-700">Ground</span>
                      </div>
                      <div className="text-sm font-medium text-slate-800">
                        {response.sufficient_evidence ? "Evidence validated" : "Abstention"}
                      </div>
                      <div className="mt-1 text-[11px] leading-5 text-slate-400">
                        Citation and evidence validation completed before the final answer.
                      </div>
                    </div>
                  </div>
                </section>

                {response.was_rewritten && response.used_query !== query && (
                  <section className="mt-5 ui-card overflow-hidden">
                    <div className="border-b border-indigo-100 bg-indigo-50/50 px-5 py-4">
                      <div className="text-xs font-semibold uppercase tracking-[0.08em] text-indigo-600">
                        Contextual query rewrite
                      </div>
                      <div className="mt-1 text-[11px] text-indigo-500">
                        The router transformed the conversational query into a retrieval-ready form.
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2">
                      <div className="border-b border-slate-100 p-5 md:border-b-0 md:border-r">
                        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                          Original
                        </div>
                        <div className="mt-2 text-sm leading-6 text-slate-600">
                          {query}
                        </div>
                      </div>

                      <div className="p-5">
                        <div className="text-[10px] font-semibold uppercase tracking-wider text-indigo-500">
                          Retrieval query
                        </div>
                        <div className="mt-2 font-mono text-xs leading-6 text-indigo-900">
                          {response.used_query}
                        </div>
                      </div>
                    </div>
                  </section>
                )}
              </div>
            )}
          </div>
        </main>
      </div>
      <style>{`
        /* Query history polish: preserve the existing component behavior while
           removing the browser-scrollbar feel and tightening the visual rhythm. */
        .query-history-polished {
          scrollbar-width: none;
        }

        .query-history-polished::-webkit-scrollbar,
        .query-history-polished *::-webkit-scrollbar {
          width: 0;
          height: 0;
        }

        .query-history-polished [class*="overflow-x-auto"],
        .query-history-polished [class*="overflow-x-scroll"] {
          scrollbar-width: none;
        }

        .query-history-polished [class*="overflow-x-auto"]::-webkit-scrollbar,
        .query-history-polished [class*="overflow-x-scroll"]::-webkit-scrollbar {
          display: none;
        }

        /* Compact initial state so the query console stays above the fold. */
        .compact-empty-state {
          padding-top: 30px !important;
          padding-bottom: 30px !important;
        }

        @media (max-width: 768px) {
          .compact-empty-state {
            padding-top: 24px !important;
            padding-bottom: 24px !important;
          }
        }
      `}</style>
    </div>
  );
}
