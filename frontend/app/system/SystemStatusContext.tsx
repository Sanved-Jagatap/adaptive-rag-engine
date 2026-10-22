"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type SystemStatus = {
  service: {
    name: string;
    environment: string;
    version: string;
    log_level: string;
  };
  dependencies: {
    api: string;
    ollama: string;
    qdrant: string;
    postgres: string;
  };
  models: {
    ollama: string;
    ollama_host: string;
    installed_ollama_models: string[];
    embedding: string;
    reranker: string;
    reranker_status: string;
  };
  retrieval: {
    strategies: string[];
    default_top_k: number;
    chunk_size: number;
    chunk_overlap: number;
    vector_dimension: number;
    distance: string;
    rrf_k: number;
  };
  qdrant: {
    collection: string;
    exists: boolean;
    points: number;
    segments: number;
    indexed_vectors: number;
    optimizer_status: string;
    vectors: {
      size: number;
      distance: string;
    };
  };
  bm25: {
    status: string;
    path: string;
    chunks: number;
  };
  paths: {
    raw_data: string;
    processed_data: string;
    bm25_corpus: string;
    routing_log: string;
  };
};

type SystemStatusContextValue = {
  data: SystemStatus | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const SystemStatusContext =
  createContext<SystemStatusContextValue | null>(null);

export function SystemStatusProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [data, setData] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = async (showLoading = false) => {
    if (showLoading) {
      setLoading(true);
    }

    try {
      const api =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      const response = await fetch(`${api}/system/status`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("Failed to load system status");
      }

      const result = (await response.json()) as SystemStatus;

      setData(result);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load system status"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadStatus(true);

    const interval = window.setInterval(() => {
      void loadStatus(false);
    }, 30000);

    return () => window.clearInterval(interval);
  }, []);

  const value = useMemo(
    () => ({
      data,
      loading,
      error,
      refresh: () => loadStatus(false),
    }),
    [data, loading, error]
  );

  return (
    <SystemStatusContext.Provider value={value}>
      {children}
    </SystemStatusContext.Provider>
  );
}

export function useSystemStatus() {
  const context = useContext(SystemStatusContext);

  if (!context) {
    throw new Error(
      "useSystemStatus must be used inside SystemStatusProvider"
    );
  }

  return context;
}
