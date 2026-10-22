import type { Source } from "@/lib/api";

interface SourceRowProps {
  source: Source;
  rank: number; // 1-indexed — matches the [Source N] numbering the generator cites by
  isCited: boolean;
}

function truncate(text: string, max = 220): string {
  if (text.length <= max) return text;
  return text.slice(0, max).trimEnd() + "…";
}

export function SourceRow({ source, rank, isCited }: SourceRowProps) {
  return (
    <li className="border border-hairline p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-sm text-ink-soft">{String(rank).padStart(2, "0")}</span>
          {isCited && (
            <span className="border border-signal-high text-signal-high px-1.5 text-xs">cited</span>
          )}
        </div>
        <span className="font-mono text-xs text-ink-soft shrink-0">
          score {source.score.toFixed(3)}
          {source.rerank_score !== null && <> · rerank {source.rerank_score.toFixed(3)}</>}
        </span>
      </div>
      <p className="mt-2 text-sm leading-relaxed">{truncate(source.text)}</p>
      <p className="mt-2 font-mono text-xs text-ink-soft/70 truncate">{source.chunk_id}</p>
    </li>
  );
}
