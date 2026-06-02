import { statusBadgeClass } from "@/lib/format";

export function StatusBadge({ label, kind }: { label: string; kind: string }) {
  return <span className={statusBadgeClass(kind)}>{label}</span>;
}
