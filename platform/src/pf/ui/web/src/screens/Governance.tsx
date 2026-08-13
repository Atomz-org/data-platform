import React from "react";
import {
  Badge, Button, Card, HStack, Input, Modal, PageHeader, SegmentedControl,
  Spinner, Table, Text, VStack,
} from "wss3-forge";
import { api, type GovEdit, type GovSurface, type Json } from "../api";

interface Doc { surface: string; group: string; path: string; exists: boolean; document: Json }

/** Flatten the YAML into editable leaves. Structural nodes are shown as
 *  context but not offered for editing — see `pf.governance.store` for why a
 *  structural change stays a file edit. */
function leaves(node: Json, prefix = ""): { path: string; value: unknown }[] {
  const out: { path: string; value: unknown }[] = [];
  for (const [k, v] of Object.entries(node ?? {})) {
    const path = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object" && !Array.isArray(v)) {
      out.push(...leaves(v as Json, path));
    } else if (!Array.isArray(v)) {
      out.push({ path, value: v });
    }
  }
  return out;
}

/**
 * Where a data owner corrects a definition.
 *
 * The write path is deliberately visible in the UI: an edit records an audit row
 * in DuckDB and then rewrites the YAML, which stays the artefact git reviews and
 * `pf check` validates. Saying so on the screen matters — an owner who believes
 * they are editing a database will not expect their change in a pull request.
 */
export default function Governance({ group }: { group: string }) {
  const [surfaces, setSurfaces] = React.useState<GovSurface[] | null>(null);
  const [surface, setSurface] = React.useState("concepts");
  const [doc, setDoc] = React.useState<Doc | null>(null);
  const [edits, setEdits] = React.useState<GovEdit[]>([]);
  const [editing, setEditing] = React.useState<{ path: string; value: string } | null>(null);
  const [actor, setActor] = React.useState(localStorage.getItem("pf-actor") ?? "");
  const [reason, setReason] = React.useState("");
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  const scoped = surfaces?.find(s => s.name === surface)?.scoped ?? false;

  const reload = React.useCallback(() => {
    api.get<Doc>("/api/governance/document",
      { surface, group: scoped ? group : "" }).then(setDoc).catch(e => setError(e.message));
    api.get<{ edits: GovEdit[] }>("/api/governance/history", { surface })
      .then(r => setEdits(r.edits)).catch(() => setEdits([]));
  }, [surface, group, scoped]);

  React.useEffect(() => {
    api.get<{ surfaces: GovSurface[] }>("/api/governance/surfaces")
      .then(r => setSurfaces(r.surfaces)).catch(e => setError(e.message));
  }, []);

  React.useEffect(() => { if (surfaces) reload(); }, [surfaces, reload]);

  async function save() {
    if (!editing) return;
    setBusy(true);
    setError("");
    try {
      await api.post("/api/governance/edit", {
        surface, key_path: editing.path, value: editing.value,
        actor, reason, group: scoped ? group : "",
      });
      localStorage.setItem("pf-actor", actor);
      setEditing(null);
      setReason("");
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function undo(id: string) {
    setError("");
    try {
      await api.post("/api/governance/revert", { edit_id: id, actor });
      reload();
    } catch (e) { setError((e as Error).message); }
  }

  if (!surfaces) return <Spinner />;

  const rows = doc ? leaves(doc.document) : [];

  return (
    <VStack gap="lg">
      <PageHeader
        title="Governance"
        subtitle="Correct a definition. Every change is audited in DuckDB, then written to the YAML that git reviews."
      />

      <SegmentedControl
        value={surface}
        onChange={setSurface}
        options={surfaces.map(s => ({ id: s.name, label: s.title }))}
      />

      {error && <Text color="error">{error}</Text>}

      <Card
        title={surfaces.find(s => s.name === surface)?.title ?? surface}
        subtitle={surfaces.find(s => s.name === surface)?.description}
      >
        <Text size="xs" color="secondary" className="pf-mono"
              style={{ display: "block", marginBottom: 12 }}>
          {doc?.path ?? ""}
        </Text>
        <div className="pf-scroll-x">
          <Table
            data={rows}
            keyField="path"
            searchable
            searchKeys={["path"]}
            searchPlaceholder="Filter by key…"
            columns={[
              {
                key: "path", header: "Definition", sortable: true,
                render: (_: unknown, r: { path: string }) =>
                  <Text className="pf-mono" size="sm">{r.path}</Text>,
              },
              {
                key: "value", header: "Value",
                render: (_: unknown, r: { value: unknown }) => <Text>{String(r.value)}</Text>,
              },
              {
                key: "edit", header: "", width: 90, align: "right" as const,
                render: (_: unknown, r: { path: string; value: unknown }) => (
                  <Button size="xs" variant="ghost"
                          onClick={() => setEditing({ path: r.path, value: String(r.value) })}>
                    Edit
                  </Button>
                ),
              },
            ]}
            emptyMessage="Nothing editable here."
          />
        </div>
      </Card>

      <Card title="Audit" subtitle="Append-only. A correction is a new row, never an overwrite.">
        <div className="pf-scroll-x">
          <Table
            data={edits}
            keyField="id"
            columns={[
              {
                key: "ts", header: "When", width: 170,
                render: (_: unknown, e: GovEdit) =>
                  <Text size="xs" className="pf-mono">{String(e.ts).slice(0, 19)}</Text>,
              },
              { key: "actor", header: "Who", width: 190 },
              {
                key: "key_path", header: "What",
                render: (_: unknown, e: GovEdit) =>
                  <Text className="pf-mono" size="sm">{e.key_path}</Text>,
              },
              {
                key: "change", header: "Change",
                render: (_: unknown, e: GovEdit) => (
                  <Text size="sm">
                    <s>{JSON.parse(e.before ?? '""')}</s> → {JSON.parse(e.after ?? '""')}
                  </Text>
                ),
              },
              { key: "reason", header: "Why" },
              {
                key: "applied", header: "", width: 110, align: "right" as const,
                render: (_: unknown, e: GovEdit) => e.applied
                  ? <Button size="xs" variant="ghost" onClick={() => undo(e.id)}>Revert</Button>
                  // A failed attempt is kept, not hidden: a file that disagrees
                  // with what someone remembers doing is exactly when you need it.
                  : <Badge variant="error">not applied</Badge>,
              },
            ]}
            emptyMessage="No edits recorded yet."
          />
        </div>
      </Card>

      <Modal open={!!editing} onClose={() => setEditing(null)} title="Correct a definition">
        <VStack gap="md">
          <Text size="sm" className="pf-mono">{editing?.path}</Text>
          <Input label="New value" value={editing?.value ?? ""}
                 onChange={(v: string) => setEditing(e => e && { ...e, value: v })} />
          <Input label="Your name or email" value={actor} onChange={setActor}
                 hint="Recorded against the change. Required." />
          <Input label="Why" value={reason} onChange={setReason}
                 hint="The definition will outlive the reason unless you write it down." />
          <HStack gap="sm" justify="end">
            <Button variant="ghost" onClick={() => setEditing(null)}>Cancel</Button>
            <Button onClick={save} loading={busy} disabled={!actor.trim()}>
              Apply and audit
            </Button>
          </HStack>
        </VStack>
      </Modal>
    </VStack>
  );
}
