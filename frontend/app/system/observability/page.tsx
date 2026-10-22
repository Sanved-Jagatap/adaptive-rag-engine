"use client";

import { useSystemStatus } from "../SystemStatusContext";

export default function ObservabilityPage() {
  const { data, loading, error } = useSystemStatus();

  if (!data && loading) {
    return (
      <main className="min-h-screen bg-slate-50 p-6 md:p-8">
        <div className="mx-auto max-w-6xl">
          <LoadingState label="Loading observability data..." />
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
              Observability
            </h1>
            <p className="mt-2 text-sm text-red-600">
              {error || "Unable to load observability data."}
            </p>
          </div>
        </div>
      </main>
    );
  }

  const services = [
    ["API", data.dependencies.api],
    ["Ollama", data.dependencies.ollama],
    ["Qdrant", data.dependencies.qdrant],
    ["PostgreSQL", data.dependencies.postgres],
  ] as const;

  const healthyServices = services.filter(([, status]) => status === "ok").length;

  return (
    <main className="min-h-screen bg-slate-50 p-6 md:p-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <section>
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-100 text-xl text-indigo-600">
              ◎
            </div>
            <div>
              <p className="text-sm font-medium text-indigo-600">System</p>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                Observability
              </h1>
              <p className="mt-1 text-sm text-slate-500">
                Runtime health, dependencies, and model availability.
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Dependency health
              </p>
              <h2 className="mt-2 text-xl font-semibold text-slate-900">
                {healthyServices} / {services.length} services healthy
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Current runtime connectivity reported by the system status API.
              </p>
            </div>

            <span
              className={`inline-flex w-fit rounded-full px-3 py-1.5 text-xs font-semibold ${
                healthyServices === services.length
                  ? "bg-emerald-50 text-emerald-600"
                  : "bg-amber-50 text-amber-600"
              }`}
            >
              {healthyServices === services.length
                ? "All systems operational"
                : "Partial availability"}
            </span>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          {services.map(([name, status]) => (
            <div
              key={name}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-base font-semibold text-slate-900">{name}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Runtime dependency
                  </p>
                </div>

                <StatusBadge
                  label={status}
                  healthy={status === "ok"}
                />
              </div>
            </div>
          ))}
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-6 py-5">
            <h2 className="text-base font-semibold text-slate-900">
              Service Runtime
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Application metadata and environment configuration.
            </p>
          </div>

          <div className="grid gap-px bg-slate-100 md:grid-cols-2">
            <Detail label="Application" value={data.service.name} />
            <Detail label="Version" value={data.service.version} />
            <Detail label="Environment" value={data.service.environment} />
            <Detail label="Log Level" value={data.service.log_level} />
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-6 py-5">
            <h2 className="text-base font-semibold text-slate-900">
              Model Runtime
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Active and installed local AI models.
            </p>
          </div>

          <div className="grid gap-px bg-slate-100 md:grid-cols-2">
            <Detail label="Active Ollama Model" value={data.models.ollama} />
            <Detail label="Ollama Host" value={data.models.ollama_host} />
            <Detail label="Embedding Model" value={data.models.embedding} />
            <Detail label="Reranker" value={data.models.reranker} />
          </div>

          <div className="border-t border-slate-100 p-6">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
              Installed Ollama Models
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              {data.models.installed_ollama_models.map((model) => (
                <span
                  key={model}
                  className={`rounded-lg border px-3 py-2 font-mono text-xs ${
                    model === data.models.ollama
                      ? "border-indigo-200 bg-indigo-50 text-indigo-700"
                      : "border-slate-200 bg-slate-50 text-slate-700"
                  }`}
                >
                  {model}
                </span>
              ))}
            </div>
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
