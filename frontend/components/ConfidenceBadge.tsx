import type { ConfidenceLevel } from "@/lib/api";

const CONFIDENCE_STYLES: Record<ConfidenceLevel, { label: string; text: string; bg: string }> = {
  high: { label: "High confidence", text: "text-signal-high", bg: "bg-signal-high-soft" },
  medium: { label: "Medium confidence", text: "text-signal-medium", bg: "bg-signal-medium-soft" },
  low: { label: "Low confidence", text: "text-signal-low", bg: "bg-signal-low-soft" },
  none: { label: "No supporting evidence", text: "text-signal-low", bg: "bg-signal-low-soft" },
};

export function ConfidenceBadge({ level }: { level: ConfidenceLevel }) {
  const style = CONFIDENCE_STYLES[level];
  return (
    <span className={`inline-flex items-center gap-1.5 border border-hairline px-2 py-1 text-sm ${style.bg} ${style.text}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
      {style.label}
    </span>
  );
}
