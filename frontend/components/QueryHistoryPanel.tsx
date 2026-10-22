"use client";

import type { QueryHistoryEntry } from "@/lib/history";

interface QueryHistoryPanelProps {
  entries: QueryHistoryEntry[];
  onSelect: (entry: QueryHistoryEntry) => void;
  onClear: () => void;
}

function truncateQuery(query: string, max = 40): string {
  return query.length > max ? query.slice(0, max).trimEnd() + "…" : query;
}

export function QueryHistoryPanel({ entries, onSelect, onClear }: QueryHistoryPanelProps) {
  // Nothing to show yet — skip rendering entirely rather than an empty
  // state that would just add clutter above the query form.
  if (entries.length === 0) return null;

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xs text-ink-soft uppercase tracking-wide">Recent queries</h2>
        <button
          onClick={onClear}
          className="text-xs text-ink-soft underline decoration-dotted hover:text-ink"
        >
          Clear
        </button>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {entries.map((entry) => (
          <button
            key={entry.id}
            type="button"
            onClick={() => onSelect(entry)}
            className="shrink-0 border border-hairline px-3 py-1.5 text-sm hover:bg-accent-soft transition-colors whitespace-nowrap"
            title={entry.query}
          >
            {truncateQuery(entry.query)}
          </button>
        ))}
      </div>
    </div>
  );
}
