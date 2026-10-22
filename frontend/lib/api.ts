// lib/api.ts
//
// Types here are hand-kept in sync with app/api/routes/query.py's
// QueryResponse model — no codegen, since the backend is small and stable
// enough that a generated OpenAPI client would be more machinery than
// this project needs. If the response shape drifts, this is the first
// place to check.

export type Strategy = "vector" | "bm25" | "hybrid";
export type ConfidenceLevel = "none" | "low" | "medium" | "high";

export interface Source {
  chunk_id: string;
  text: string;
  score: number;
  rerank_score: number | null;
}

export interface QueryResponse {
  answer: string;
  cited_sources: number[];
  invalid_citations: number[];
  sufficient_evidence: boolean;
  confidence_level: ConfidenceLevel;
  citation_coverage: number;
  sources: Source[];
  strategy: Strategy;
  decided_by: string;
  was_rewritten: boolean;
  used_query: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function runQuery(query: string, topK = 5, recentContext = ""): Promise<QueryResponse> {
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE_URL}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: topK, recent_context: recentContext }),
    });
  } catch {
    throw new ApiError(
      `Couldn't reach the API at ${API_BASE_URL}. Is the backend running?`,
    );
  }

  if (!resp.ok) {
    const body = await resp.text().catch(() => "");
    throw new ApiError(`Query failed (${resp.status}): ${body || resp.statusText}`, resp.status);
  }

  return resp.json();
}