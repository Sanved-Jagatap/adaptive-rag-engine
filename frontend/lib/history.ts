// lib/history.ts
//
// Client-side query history via localStorage. No backend involvement —
// this is per-browser, not per-user-account, which matches this project's
// scope (a query console for one person to explore the corpus, not a
// multi-user product with auth).

import type { QueryResponse } from "./api";

export interface QueryHistoryEntry {
  id: string;
  query: string;
  timestamp: number;
  response: QueryResponse;
}

const STORAGE_KEY = "adaptive-rag-query-history";
const MAX_ENTRIES = 20;

export function loadHistory(): QueryHistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    // Corrupted JSON or inaccessible storage (private browsing, disabled
    // storage) shouldn't crash the app — just start with empty history.
    return [];
  }
}

export function saveHistoryEntry(entry: QueryHistoryEntry): QueryHistoryEntry[] {
  const updated = [entry, ...loadHistory()].slice(0, MAX_ENTRIES);
  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    } catch {
      // Storage full or disabled — history just won't persist this run;
      // not worth surfacing as a user-facing error for a convenience feature.
    }
  }
  return updated;
}

export function clearHistory(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
