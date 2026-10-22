export function InfoTag({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-baseline gap-1.5 border border-hairline px-2 py-1 text-sm">
      <span className="text-ink-soft">{label}</span>
      <span className="font-medium">{value}</span>
    </span>
  );
}
