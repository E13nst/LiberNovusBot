import Link from "next/link";
import { notFound } from "next/navigation";

import { StatusBadge } from "@/components/StatusBadge";
import { adminFetch, isPositiveIntegerString, type DreamView } from "@/lib/api";
import { formatTimestamp, ownerLabel, shortId } from "@/lib/format";

export default async function DreamPage({ params }: { params: Promise<{ id?: string }> }) {
  const { id } = await params;
  if (!isPositiveIntegerString(id)) {
    notFound();
  }

  const dream = await adminFetch<DreamView>(`/admin/api/dreams/${id}`);

  return (
    <section>
      <Link className="back-link" href={`/sessions/${dream.session_id}`}>
        ← Back to session {shortId(dream.session_id)}
      </Link>

      <div className="card dream-detail" style={{ marginTop: 16 }}>
        <div className="session-card-header">
          <StatusBadge kind="DREAM_CREATED" label={`Dream #${dream.id}`} />
          <span className="muted">{formatTimestamp(dream.created_at)}</span>
        </div>
        <h1>Captured dream message</h1>
        <p className="sensitive-note">Sensitive user input — visible only in this admin console.</p>

        <dl className="meta-list">
          <div>
            <dt>Owner</dt>
            <dd>{ownerLabel(dream.user_id)}</dd>
          </div>
          <div>
            <dt>Session</dt>
            <dd>
              <Link href={`/sessions/${dream.session_id}`}>{shortId(dream.session_id)}</Link>
            </dd>
          </div>
          <div>
            <dt>Captured at</dt>
            <dd>{formatTimestamp(dream.created_at)}</dd>
          </div>
        </dl>

        <div className="dream-text-block">
          <h2>Raw input</h2>
          <p className="dream-text">{dream.text}</p>
        </div>
      </div>
    </section>
  );
}
