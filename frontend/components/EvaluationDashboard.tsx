"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchEvaluationResults,
  type EvaluationResults,
  type RetrievalMetrics,
  type GenerationMetrics,
} from "@/lib/evaluation";
import { ApiError } from "@/lib/api";

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function MetricCard({
  label,
  value,
  description,
}: {
  label: string;
  value: string;
  description: string;
}) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      <div className="metric-description">
        {description}
      </div>
    </div>
  );
}

function RetrievalRow({
  label,
  m,
}: {
  label: string;
  m: RetrievalMetrics;
}) {
  return (
    <tr>
      <td className="font-medium text-slate-800">
        {label}
      </td>
      <td className="font-mono">
        {m.recall_at_k.toFixed(3)}
      </td>
      <td className="font-mono">
        {m.precision_at_k.toFixed(3)}
      </td>
      <td className="font-mono">
        {m.mrr.toFixed(3)}
      </td>
      <td className="font-mono text-slate-400">
        {m.num_queries}
      </td>
    </tr>
  );
}

function GenerationRow({
  label,
  m,
}: {
  label: string;
  m: GenerationMetrics;
}) {
  return (
    <tr>
      <td className="font-medium text-slate-800">
        {label}
      </td>

      <td className="font-mono">
        {pct(m.sufficient_evidence_rate)}
      </td>

      <td className="font-mono">
        {m.num_judged > 0
          ? m.avg_faithfulness.toFixed(2)
          : "—"}
      </td>

      <td className="font-mono">
        {m.num_judged > 0
          ? m.avg_relevance.toFixed(2)
          : "—"}
      </td>

      <td className="font-mono">
        {m.avg_total_ms.toFixed(0)}ms
      </td>

      <td className="font-mono text-slate-400">
        {m.num_queries}
      </td>
    </tr>
  );
}

export function EvaluationDashboard() {
  const [results, setResults] =
    useState<EvaluationResults | null>(null);

  const [error, setError] =
    useState<string | null>(null);

  const [loading, setLoading] =
    useState(true);

  useEffect(() => {
    fetchEvaluationResults()
      .then(setResults)
      .catch((err) =>
        setError(
          err instanceof ApiError
            ? err.message
            : "Failed to load evaluation results.",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="skeleton h-5 w-40" />
        <div className="grid grid-cols-4 gap-3">
          <div className="skeleton h-28" />
          <div className="skeleton h-28" />
          <div className="skeleton h-28" />
          <div className="skeleton h-28" />
        </div>
        <div className="skeleton h-64" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-6">
        <div className="text-sm font-medium text-red-700">
          Evaluation data unavailable
        </div>

        <div className="mt-1 text-xs text-red-600">
          {error}
        </div>
      </div>
    );
  }

  if (!results) {
    return null;
  }

  const categories = Array.from(
    new Set([
      ...Object.keys(results.baseline.by_category),
      ...Object.keys(results.adaptive.by_category),
    ]),
  ).sort();

  const overall = results.adaptive.overall;

  const generationOverall =
    results.generation?.overall;

  return (
    <div className="space-y-8">
      {results.stub_mode && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4">
          <div className="text-sm font-medium text-amber-800">
            Stub evaluation
          </div>

          <div className="mt-1 text-xs leading-5 text-amber-700">
            This run used <code>--stub</code> mode.
            The values verify pipeline execution but
            should not be interpreted as real retrieval
            or generation quality measurements.
          </div>
        </div>
      )}

      {/* KPI cards */}
      <section>
        <div className="mb-3 flex items-end justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              Run summary
            </div>

            <div className="mt-1 text-[11px] text-slate-400">
              Adaptive RAG evaluation · top-{results.k}
            </div>
          </div>

          <div className="status-pill">
            <span className="status-dot" />
            Real evaluation
          </div>
        </div>

        <div className="metric-grid">
          <MetricCard
            label={`Recall@${results.k}`}
            value={overall.recall_at_k.toFixed(3)}
            description="Adaptive retrieval coverage"
          />

          <MetricCard
            label={`Precision@${results.k}`}
            value={overall.precision_at_k.toFixed(3)}
            description="Relevant results in top-k"
          />

          <MetricCard
            label="MRR"
            value={overall.mrr.toFixed(3)}
            description="Rank of first relevant result"
          />

          <MetricCard
            label="Queries"
            value={overall.num_queries.toString()}
            description="Evaluation samples"
          />
        </div>
      </section>

      {/* Generation quality */}
      {generationOverall && (
        <section>
          <div className="mb-3">
            <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              Generation quality
            </div>

            <div className="mt-1 text-[11px] text-slate-400">
              Grounding, faithfulness, relevance, and
              latency
            </div>
          </div>

          <div className="metric-grid">
            <MetricCard
              label="Sufficient evidence"
              value={pct(
                generationOverall.sufficient_evidence_rate,
              )}
              description="Answers with validated evidence"
            />

            <MetricCard
              label="Faithfulness"
              value={
                generationOverall.num_judged > 0
                  ? generationOverall.avg_faithfulness.toFixed(
                      2,
                    )
                  : "—"
              }
              description="LLM-as-judge groundedness"
            />

            <MetricCard
              label="Relevance"
              value={
                generationOverall.num_judged > 0
                  ? generationOverall.avg_relevance.toFixed(
                      2,
                    )
                  : "—"
              }
              description="Answer relevance to query"
            />

            <MetricCard
              label="Avg latency"
              value={`${generationOverall.avg_total_ms.toFixed(
                0,
              )}ms`}
              description="End-to-end generation latency"
            />
          </div>
        </section>
      )}

      {/* Retrieval comparison */}
      <section>
        <div className="mb-3">
          <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Retrieval comparison
          </div>

          <div className="mt-1 text-[11px] text-slate-400">
            Vector baseline versus adaptive retrieval
          </div>
        </div>

        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Configuration</th>
                <th>Recall@{results.k}</th>
                <th>Precision@{results.k}</th>
                <th>MRR</th>
                <th>N</th>
              </tr>
            </thead>

            <tbody>
              <RetrievalRow
                label="Vector RAG · baseline"
                m={results.baseline.overall}
              />

              <RetrievalRow
                label="Adaptive RAG"
                m={results.adaptive.overall}
              />
            </tbody>
          </table>
        </div>
      </section>

      {/* Category breakdown */}
      <section>
        <div className="mb-3">
          <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
            Adaptive retrieval by category
          </div>

          <div className="mt-1 text-[11px] text-slate-400">
            Performance across lexical, semantic, hybrid,
            and ambiguous queries
          </div>
        </div>

        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Recall@{results.k}</th>
                <th>Precision@{results.k}</th>
                <th>MRR</th>
                <th>N</th>
              </tr>
            </thead>

            <tbody>
              {categories.map((cat) => {
                const m =
                  results.adaptive.by_category[cat];

                return m ? (
                  <RetrievalRow
                    key={cat}
                    label={cat}
                    m={m}
                  />
                ) : null;
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Generation category breakdown */}
      {results.generation && (
        <section>
          <div className="mb-3">
            <div className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              Generation by category
            </div>

            <div className="mt-1 text-[11px] text-slate-400">
              Grounding quality and latency across query
              classes
            </div>
          </div>

          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Scope</th>
                  <th>Sufficient evidence</th>
                  <th>Faithfulness</th>
                  <th>Relevance</th>
                  <th>Avg latency</th>
                  <th>N</th>
                </tr>
              </thead>

              <tbody>
                <GenerationRow
                  label="Overall"
                  m={results.generation.overall}
                />

                {categories.map((cat) => {
                  const m =
                    results.generation!.by_category[
                      cat
                    ];

                  return m ? (
                    <GenerationRow
                      key={cat}
                      label={cat}
                      m={m}
                    />
                  ) : null;
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Footer */}
      {results.generated_at && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-5">
          <div className="text-[11px] text-slate-400">
            Last evaluation run
          </div>

          <div className="font-mono text-[11px] text-slate-500">
            {new Date(
              results.generated_at,
            ).toLocaleString()}
          </div>
        </div>
      )}

      <div className="border-t border-slate-200 pt-5">
        <Link
          href="/"
          className="text-xs font-medium text-indigo-600 hover:text-indigo-700"
        >
          ← Back to query console
        </Link>
      </div>
    </div>
  );
}