import { computePipelineStatus, pipelineSummary } from "@/lib/format";
import type { AdminSession } from "@/lib/api";

import { StatusBadge } from "./StatusBadge";

export function PipelineSummary({
  session
}: {
  session: Pick<AdminSession, "dream_count" | "job_count" | "analysis_count">;
}) {
  const status = computePipelineStatus(session);

  return (
    <div className="pipeline">
      <div className="pipeline-row">
        <span className="pipeline-label">Pipeline</span>
        <span className="pipeline-value">{pipelineSummary(session)}</span>
      </div>
      <div className="pipeline-row">
        <StatusBadge kind={status.kind} label={status.label} />
        {status.hint ? <p className="muted pipeline-hint">{status.hint}</p> : null}
      </div>
    </div>
  );
}
