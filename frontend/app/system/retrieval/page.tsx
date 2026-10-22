"use client";

import { useSystemStatus } from "../SystemStatusContext";

export default function RetrievalEnginePage() {
  const { data, loading, error } = useSystemStatus();

  if (!data && loading) {
    return (
      <main className="min-h-screen bg-slate-50 p-6 md:p-8">
        <div className="mx-auto max-w-6xl">
          <LoadingState label="Loading retrieval status..." />
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
              Retrieval Engine
            </h1>
            <p className="mt-2 text-sm text-red-600">
              {error || "Unable to load system status."}
            </p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 p-6 md:p-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <section>
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-100 text-xl text-indigo-600">
              ◈
            </div>
            <div>
              <p className="text-sm font-medium text-indigo-600">System</p>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                Retrieval Engine
              </h1>
              <p className="mt-1 text-sm text-slate-500">
                Retrieval strategies, ranking models, and pipeline configuration.
              </p>
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          {data.retrieval.strategies.map((strategy) => (
            <div
              key={strategy}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium capitalize text-slate-500">
                  Strategy
                </span>
                <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-600">
                  Available
                </span>
              </div>

              <h2 className="mt-4 text-xl font-semibold capitalize text-slate-900">
                {strategy}
              </h2>

              <p className="mt-2 text-sm text-slate-500">
                {strategy === "vector" &&
                  "Semantic similarity retrieval using embedding vectors."}
                {strategy === "bm25" &&
                  "Lexical retrieval using BM25 term-based matching."}
                {strategy === "hybrid" &&
                  "Combines vector and lexical retrieval using reciprocal rank fusion."}
              </p>
            </div>
          ))}
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-6 py-5">
            <h2 className="text-base font-semibold text-slate-900">
              Model Configuration
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Models currently configured for the RAG pipeline.
            </p>
          </div>

          <div className="grid gap-0 md:grid-cols-2">
            <Detail label="Generation Model" value={data.models.ollama} note="Ollama" />
            <Detail
              label="Embedding Model"
              value={data.models.embedding}
              note={`${data.retrieval.vector_dimension}-dimensional embeddings`}
            />
            <div className="border-b border-slate-100 p-6 md:border-r">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Reranker
              </p>
              <p className="mt-2 break-all font-mono text-sm text-slate-900">
                {data.models.reranker}
              </p>
              <span className="mt-2 inline-flex rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-600">
                {data.models.reranker_status}
              </span>
            </div>
            <Detail label="Ollama Host" value={data.models.ollama_host} />
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-6 py-5">
            <h2 className="text-base font-semibold text-slate-900">
              Retrieval Configuration
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Runtime parameters used by the retrieval pipeline.
            </p>
          </div>

          <div className="grid gap-px bg-slate-100 md:grid-cols-3">
            <Metric label="Default Top-K" value={String(data.retrieval.default_top_k)} />
            <Metric label="Chunk Size" value={`${data.retrieval.chunk_size} tokens`} />
            <Metric label="Chunk Overlap" value={`${data.retrieval.chunk_overlap} tokens`} />
            <Metric label="Vector Dimension" value={String(data.retrieval.vector_dimension)} />
            <Metric label="Distance" value={data.retrieval.distance} />
            <Metric label="RRF K" value={String(data.retrieval.rrf_k)} />
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">
            Retrieval Pipeline
          </h2>

          <div className="mt-6 flex flex-wrap items-center gap-2 text-sm">
            <PipelineStep label="Query" />
            <Arrow />
            <PipelineStep label="Routing" />
            <Arrow />
            <PipelineStep label="Vector / BM25 / Hybrid" />
            <Arrow />
            <PipelineStep label="Reranking" />
            <Arrow />
            <PipelineStep label="Context" />
          </div>
        </section>
      </div>
    </main>
  );
}

function Detail({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="border-b border-slate-100 p-6">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <p className="mt-2 break-all font-mono text-sm text-slate-900">
        {value}
      </p>
      {note && <p className="mt-1 text-xs text-slate-500">{note}</p>}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white p-6">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <p className="mt-2 text-lg font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function PipelineStep({ label }: { label: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 font-medium text-slate-700">
      {label}
    </div>
  );
}

function Arrow() {
  return <span className="px-1 text-slate-300">→</span>;
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
