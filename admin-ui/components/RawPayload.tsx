import { formatJson } from "@/lib/api";

export function RawPayload({ title, value }: { title: string; value: unknown }) {
  return (
    <details className="raw-payload">
      <summary>{title}</summary>
      <pre>{formatJson(value)}</pre>
    </details>
  );
}
