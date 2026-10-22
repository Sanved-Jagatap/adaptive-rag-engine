"use client";

import { useSystemStatus } from "../SystemStatusContext";

export default function EvidenceIndexPage() {
  const { data, loading, error } = useSystemStatus();

  if (!data && loading) {
    return (
      <main className="min-h-screen bg-slate-50 p-6 md:p-8">
        <div className="mx-auto max-w-6xl">
          <LoadingState label="Loading evidence index..." />
        </div>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="min-h-screen bg-slate-50 p-6 md:p-8">
        <div className="mx-auto max-w-6xl">
          <div className="rounded-2xl border border-red-200 bg-white p-8 shadow-sm">
            <h1 className="text-lg font-semibold text-slate-900">
              Evidence Index
            </h1>
            <p className="mt-2 text-sm text-red-600">
              {error || "Unable to load index status."}
            </p>
          </div>
        </div>
      </main>
    );
  }

  const qdrantHealthy =
    data.dependencies.qdrant === "ok" &&
    data.qdrant.exists &&
    data.qdrant.optimizer_status === "ok";

  const indexAligned = data.qdrant.points === data.bm25.chunks;

  return (
    <main className="min-h-screen bg-slate-50 p-6 md:p-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <section>
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-100 text-xl text-indigo-600">
              ◇
            </div>
            <div>
              <p className="text-sm font-medium text-indigo-600">System</p>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                Evidence Index
              </h1>
              <p className="mt-1 text-sm text-slate-500">
                Vector and lexical evidence stores used by the retrieval pipeline.
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Index health
              </p>
              <h2 className="mt-2 text-xl font-semibold text-slate-900">
                {qdrantHealthy && indexAligned
                  ? "Healthy and synchronized"
                  : "Attention required"}
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Qdrant and BM25 currently contain{" "}
                <span className="font-semibold text-slate-700">{data.qdrant.points}</span>{" "}
                and{" "}
                <span className="font-semibold text-slate-700">{data.bm25.chunks}</span>{" "}
                chunks respectively.
              </p>
            </div>
            <StatusBadge
              label={qdrantHealthy && indexAligned ? "Healthy" : "Needs attention"}
              healthy={qdrantHealthy && indexAligned}
            />
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-4">
          <StatCard label="Qdrant Points" value={String(data.qdrant.points)} description="Stored vector records" />
          <StatCard label="BM25 Chunks" value={String(data.bm25.chunks)} description="Lexical index records" />
          <StatCard label="Vector Dimension" value={String(data.qdrant.vectors.size)} description="Embedding dimensions" />
          <StatCard label="Segments" value={String(data.qdrant.segments)} description="Qdrant storage segments" />
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5">
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                Qdrant Vector Index
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Semantic evidence store.
              </p>
            </div>
            <StatusBadge
              label={data.dependencies.qdrant}
              healthy={data.dependencies.qdrant === "ok"}
            />
          </div>

          <div className="grid gap-px bg-slate-100 md:grid-cols-3">
            <Detail label="Collection" value={data.qdrant.collection} />
            <Detail label="Points" value={String(data.qdrant.points)} />
            <Detail label="Segments" value={String(data.qdrant.segments)} />
            <Detail label="Vector Size" value={String(data.qdrant.vectors.size)} />
            <Detail label="Distance" value={data.qdrant.vectors.distance} />
            <Detail label="Optimizer" value={data.qdrant.optimizer_status} />
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5">
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                BM25 Lexical Index
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Keyword-based evidence store.
              </p>
            </div>
            <StatusBadge
              label={data.bm25.status}
              healthy={data.bm25.status === "ok"}
            />
          </div>

          <div className="grid gap-px bg-slate-100 md:grid-cols-2">
            <Detail label="Indexed Chunks" value={String(data.bm25.chunks)} />
            <Detail label="Status" value={data.bm25.status} />
            <div className="bg-white p-6 md:col-span-2">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Persistence Path
              </p>
              <p className="mt-2 break-all font-mono text-sm text-slate-700">
                {data.bm25.path}
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">
            Index Consistency
          </h2>

          <div className="mt-5 space-y-4">
            <ConsistencyRow label="Qdrant collection exists" value={data.qdrant.exists} />
            <ConsistencyRow
              label="Qdrant optimizer healthy"
              value={data.qdrant.optimizer_status === "ok"}
            />
            <ConsistencyRow
              label="BM25 index available"
              value={data.bm25.status === "ok"}
            />
            <ConsistencyRow
              label="Vector and lexical chunk counts aligned"
              value={indexAligned}
            />
          </div>
        </section>
      </div>
    </main>
  );
}

function LoadingState({ label }: { label: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <div className="flex items-center gap-3 text-sm text-slate-600">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-500" />
        {label}
      </div>
    </div>
  );
}

function StatusBadge({
  label,
  healthy,
}: {
  label: string;
  healthy: boolean;
}) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
        healthy
          ? "bg-emerald-50 text-emerald-600"
          : "bg-red-50 text-red-600"
      }`}
    >
      {label}
    </span>
  );
}

function StatCard({
  label,
  value,
  description,
}: {
  label: string;
  value: string;
  description: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <p className="mt-3 text-2xl font-bold text-slate-900">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{description}</p>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white p-6">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <p className="mt-2 break-all font-mono text-sm font-medium text-slate-800">
        {value}
      </p>
    </div>
  );
}

function ConsistencyRow({
  label,
  value,
}: {
  label: string;
  value: boolean;
}) {
  return (
    <div className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
      <span className="text-sm text-slate-700">{label}</span>
      <span
        className={`text-sm font-semibold ${
          value ? "text-emerald-600" : "text-red-600"
        }`}
      >
        {value ? "✓ Pass" : "✕ Check"}
      </span>
    </div>
  );
}
