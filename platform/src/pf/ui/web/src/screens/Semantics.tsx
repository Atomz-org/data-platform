import React from "react";
import {
  Badge, Button, Card, CodeBlock, Grid, HStack, KpiCard, PageHeader, Spinner,
  Table, Text, Textarea, VStack,
} from "wss3-forge";
import { api, type Json } from "../api";

interface Mdl {
  catalog: string; schema: string; data_source: string;
  models: { name: string; table: string; schema: string; columns: number; roles: string[] }[];
  relationships: Json[];
  engine: { ok: boolean; detail: string };
}

/**
 * Ask the semantic layer a question and get rows back.
 *
 * Wren expands the query against the MDL; the platform executes the expansion
 * against its own read-only warehouse connection. Both halves are shown — the
 * planned SQL is the part a reviewer needs when the answer looks wrong, and
 * hiding it would make the semantic layer a black box that returns numbers.
 */
export default function Semantics({ group, project }: { group: string; project: string }) {
  const [mdl, setMdl] = React.useState<Mdl | null>(null);
  const [sql, setSql] = React.useState(
    "select customer_segment, sum(net_amount) as net\nfrom fct_revenue group by 1");
  const [result, setResult] = React.useState<Json | null>(null);
  const [running, setRunning] = React.useState(false);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    setMdl(null);
    api.get<Mdl>("/api/wren/mdl", { group, project }).then(setMdl)
      .catch(e => setError(e.message));
  }, [group, project]);

  async function run() {
    setRunning(true);
    setResult(null);
    setError("");
    try {
      setResult(await api.post<Json>("/api/wren/query", { group, project, sql }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  if (error && !mdl) return <Text color="error">{error}</Text>;
  if (!mdl) return <Spinner />;

  const engineOk = mdl.engine?.ok;

  return (
    <VStack gap="lg">
      <PageHeader
        title="Semantic layer"
        subtitle={`${mdl.catalog}.${mdl.schema} — the MDL an external consumer receives`}
      />

      <Grid columns={{ xs: 2, lg: 4 }} gap="md">
        <KpiCard label="MDL models" value={mdl.models.length} delta={{ text: "published entities", tone: "flat" }} />
        <KpiCard label="Relationships" value={mdl.relationships.length} delta={{ text: "from the graph", tone: "flat" }} />
        <KpiCard label="Data source" value={mdl.data_source || "—"} delta={{ text: "MDL dataSource", tone: "flat" }} />
        <KpiCard label="Planner" value={engineOk ? "ready" : "unusable"}
                 delta={{ text: engineOk ? "plans MDL queries" : (mdl.engine?.detail ?? "").slice(0, 40),
                          tone: engineOk ? "up" : "down" }} />
      </Grid>

      <Card title="Ask the semantic layer"
            subtitle="Wren expands the query against the MDL; the warehouse connection stays ours, and read-only">
        <VStack gap="md">
          <Textarea value={sql} onChange={setSql} rows={4} className="pf-mono"
                    aria-label="Query against the semantic layer" />
          <HStack gap="sm">
            <Button onClick={run} loading={running} disabled={!engineOk}>
              Run
            </Button>
            {!engineOk && (
              <Text size="sm" color="secondary">
                The planner cannot resolve models in this environment.
              </Text>
            )}
          </HStack>

          {error && <Text color="error">{error}</Text>}

          {result && result.ok === false && (
            <VStack gap="xs">
              <Text color="error">{String(result.reason ?? "failed")}</Text>
              <CodeBlock code={String(result.message ?? "")} language="text" />
            </VStack>
          )}

          {result?.ok && (
            <VStack gap="md">
              <div className="pf-scroll-x">
                <Table
                  data={(result.rows as Json[]) ?? []}
                  columns={((result.columns as string[]) ?? []).map(c => ({
                    key: c, header: c,
                    render: (v: unknown) => (
                      <Text className={typeof v === "number" ? "pf-num" : undefined}>
                        {String(v)}
                      </Text>
                    ),
                  }))}
                  emptyMessage="The query returned no rows."
                />
              </div>
              {/* Shown, not hidden: when a number looks wrong this is the
                  first thing anyone needs to see. */}
              <CodeBlock code={String(result.sql ?? "")} language="sql" />
            </VStack>
          )}
        </VStack>
      </Card>

      <Card title="MDL models">
        <div className="pf-scroll-x">
          <Table
            data={mdl.models}
            keyField="name"
            sortable
            columns={[
              {
                key: "name", header: "Model", sortable: true,
                render: (_: unknown, r: Mdl["models"][number]) =>
                  <Text className="pf-mono">{r.name}</Text>,
              },
              {
                key: "table", header: "Relation",
                render: (_: unknown, r: Mdl["models"][number]) =>
                  <Text className="pf-mono" color="secondary">{r.schema}.{r.table}</Text>,
              },
              { key: "columns", header: "Cols", align: "right" as const, sortable: true },
              {
                key: "roles", header: "Ontology roles",
                render: (_: unknown, r: Mdl["models"][number]) => (
                  <HStack gap="xs" wrap>
                    {r.roles.map(x => <Badge key={x}>{x}</Badge>)}
                  </HStack>
                ),
              },
            ]}
            emptyMessage="No MDL yet — run pf bootstrap."
          />
        </div>
      </Card>
    </VStack>
  );
}
