// lib/evaluation.ts
//
// Types here are hand-kept in sync with app/evaluation/runner.py's
// aggregate_results() / aggregate_generation_results() dict shapes, and
// scripts/run_evaluation.py's output_data assembly — same "no codegen"
// approach as lib/api.ts.

export interface RetrievalMetrics {
  recall_at_k: number;
  precision_at_k: number;
  mrr: number;
  num_queries: number;
}

export interface RetrievalAggregate {
  overall: RetrievalMetrics;
  by_category: Record<string, RetrievalMetrics>;
}

export interface GenerationMetrics {
  sufficient_evidence_rate: number;
  avg_faithfulness: number;
  avg_relevance: number;
  num_judged: number;
  avg_prompt_tokens: number | null;
  avg_completion_tokens: number | null;
  avg_total_ms: number;
  avg_generation_ms: number;
  num_queries: number;
}

export interface GenerationAggregate {
  overall: GenerationMetrics;
  by_category: Record<string, GenerationMetrics>;
}

export interface EvaluationResults {
  k: number;
  stub_mode: boolean;
  generated_at?: string;
  baseline: RetrievalAggregate;
  adaptive: RetrievalAggregate;
  generation: GenerationAggregate | null;
}

import { ApiError } from "./api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchEvaluationResults(): Promise<EvaluationResults> {
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE_URL}/evaluation/results`);
  } catch {
    throw new ApiError(`Couldn't reach the API at ${API_BASE_URL}. Is the backend running?`);
  }

  if (resp.status === 404) {
    throw new ApiError(
      "No evaluation results yet — run `python scripts/run_evaluation.py` on the backend first.",
      404,
    );
  }

  if (!resp.ok) {
    const body = await resp.text().catch(() => "");
    throw new ApiError(`Failed to load evaluation results (${resp.status}): ${body || resp.statusText}`, resp.status);
  }

  return resp.json();
}
