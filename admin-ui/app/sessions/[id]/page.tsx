import Link from "next/link";
import { notFound } from "next/navigation";

import { PipelineSummary } from "@/components/PipelineSummary";
import { PolicyTraceCard } from "@/components/PolicyTraceCard";
import { StatusBadge } from "@/components/StatusBadge";
import { TimelineEvent } from "@/components/TimelineEvent";
import {
  adminFetch,
  isUuid,
  type AdminSession,
  type DreamView,
  type EventView,
  type PolicyTrace
} from "@/lib/api";
import { formatTimestamp, ownerLabel, shortId } from "@/lib/format";

export default async function SessionDetailPage({ params }: { params: Promise<{ id?: string }> }) {
  const { id } = await params;
  if (!isUuid(id)) {
    notFound();
  }

  const [session, dreams, policy, trace] = await Promise.all([
    adminFetch<AdminSession>(`/admin/api/sessions/${id}`),
    adminFetch<{ dreams: DreamView[] }>(`/admin/api/sessions/${id}/dreams`),
    adminFetch<{ policy_traces: PolicyTrace[] }>(`/admin/api/sessions/${id}/policy`),
    adminFetch<{ timeline: EventView[] }>(`/admin/api/sessions/${id}/trace`)
  ]);

  return (
    <section>
      <Link className="back-link" href="/sessions">
        ← Back to sessions
      </Link>

      <div className="card session-summary" style={{ marginTop: 16 }}>
        <div className="session-card-header">
          <StatusBadge kind={session.status} label={session.status} />
          <span className="muted">Last activity: {formatTimestamp(session.last_activity_at)}</span>
        </div>
        <h1>Session {shortId(session.id)}</h1>
        <dl className="meta-list">
          <div>
            <dt>Owner</dt>
            <dd>{ownerLabel(session.user_id)}</dd>
          </div>
          <div>
            <dt>Full session ID</dt>
            <dd>{session.id}</dd>
          </div>
          <div>
            <dt>Policy traces</dt>
            <dd>{session.policy_trace_count ?? 0}</dd>
          </div>
        </dl>
        <PipelineSummary session={session} />
      </div>

      <div className="section-block">
        <h2>Policy Trace</h2>
        <p className="muted">
          For each inbound message: input → route → rule → execution outcome. This is the main debug surface for
          &quot;why did the bot respond this way?&quot;
        </p>
        <div className="stack">
          {policy.policy_traces.map((item) => (
            <PolicyTraceCard key={item.id} trace={item} />
          ))}
          {policy.policy_traces.length === 0 ? (
            <div className="card">
              <p className="muted">No policy traces recorded for this session.</p>
            </div>
          ) : null}
        </div>
      </div>

      <div className="section-block">
        <h2>Captured Dreams</h2>
        <div className="card">
          {dreams.dreams.map((dream) => (
            <div className="dream-row" key={dream.id}>
              <Link href={`/dream/${dream.id}`}>Dream #{dream.id}</Link>
              <span className="muted">{formatTimestamp(dream.created_at)}</span>
            </div>
          ))}
          {dreams.dreams.length === 0 ? <p className="muted">No dreams persisted for this session.</p> : null}
        </div>
      </div>

      <div className="section-block">
        <h2>Trace Timeline</h2>
        <p className="muted">Chronological story of inputs, policy decisions, dream capture, jobs, and reflections.</p>
        <div className="timeline">
          {trace.timeline.map((event) => (
            <TimelineEvent key={event.id} event={event} />
          ))}
          {trace.timeline.length === 0 ? (
            <div className="card">
              <p className="muted">No timeline events yet.</p>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
