import Link from "next/link";
import type { ReactNode } from "react";

import type { EventView } from "@/lib/api";
import { eventTypeLabel, formatTimestamp, truncateText } from "@/lib/format";

import { RawPayload } from "./RawPayload";
import { StatusBadge } from "./StatusBadge";

export function TimelineEvent({ event }: { event: EventView }) {
  return (
    <article className="timeline-item">
      <div className="timeline-item-header">
        <StatusBadge kind={event.type} label={eventTypeLabel(event.type)} />
        <span className="muted">{formatTimestamp(event.timestamp)}</span>
      </div>
      <div className="timeline-summary">{renderSummary(event)}</div>
      <RawPayload title="Raw event payload" value={event.payload} />
    </article>
  );
}

function renderSummary(event: EventView): ReactNode {
  const payload = event.payload;

  switch (event.type) {
    case "INPUT": {
      const text = typeof payload.text === "string" ? payload.text : null;
      return text ? <p className="timeline-text">{truncateText(text, 220)}</p> : <p className="muted">Input recorded.</p>;
    }
    case "POLICY": {
      const decision = payload.decision as Record<string, unknown> | undefined;
      const route = typeof decision?.route === "string" ? decision.route : "unknown route";
      const reason =
        typeof decision?.reason_code === "string" ? decision.reason_code : "unknown rule";
      return (
        <p>
          Routed to <strong>{route}</strong> via <strong>{reason}</strong>
        </p>
      );
    }
    case "CLARIFICATION":
      return <p className="muted">Immediate clarification response sent; no dream or job created.</p>;
    case "DREAM_CREATED": {
      const dreamId = payload.dream_id;
      const text = typeof payload.text === "string" ? payload.text : null;
      return (
        <>
          {typeof dreamId === "number" ? (
            <p>
              <Link href={`/dream/${dreamId}`}>Dream #{dreamId}</Link> captured.
            </p>
          ) : (
            <p>Dream captured.</p>
          )}
          {text ? <p className="timeline-text">{truncateText(text, 180)}</p> : null}
        </>
      );
    }
    case "JOB_ENQUEUED": {
      const status = typeof payload.status === "string" ? payload.status : "unknown";
      const jobId = typeof payload.job_id === "string" ? payload.job_id : null;
      return (
        <p>
          Reflection job {jobId ? `#${jobId.slice(0, 8)}…` : ""} queued with status <strong>{status}</strong>.
        </p>
      );
    }
    case "REFLECTION_READY": {
      const analysisId = typeof payload.analysis_id === "string" ? payload.analysis_id : null;
      return (
        <p>
          Reflection completed{analysisId ? ` (analysis ${analysisId.slice(0, 8)}…)` : ""}.
        </p>
      );
    }
    default:
      return null;
  }
}
