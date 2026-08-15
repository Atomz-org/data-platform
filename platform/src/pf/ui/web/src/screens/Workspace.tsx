import React from "react";
import {
  Badge, Card, EmptyState, Grid, HStack, KpiCard, PageHeader, Spinner,
  Table, Text, VStack,
} from "wss3-forge";
import { Board24Regular } from "@fluentui/react-icons";
import { api, type SemanticDiff, type SemanticRow } from "../api";
import { Verdict } from "../components/Verdict";

/**
 * The join: every published semantic entity against what the review measured on
 * the model behind it. Two panels side by side made the reader correlate by eye;
 * this is the correlation, done once, server side.
 */
export default function Workspace({ group, project }: { group: string; project: string }) {
  const [data, setData] = React.useState<SemanticDiff | null>(null);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    setData(null);
    setError("");
    api.get<SemanticDiff>("/api/workspace/semantic-diff", { group, project })
      .then(setData).catch(e => setError(e.message));
  }, [group, project]);

  if (error) return <Text color="error">{error}</Text>;
  if (!data) return <Spinner />;

  if (!data.wren_enabled || !data.recce_enabled) {
    const off = [!data.wren_enabled && "wren", !data.recce_enabled && "recce"]
      .filter(Boolean).join(" and ");
    return (
      <EmptyState
        icon={<Board24Regular />}
        title="This view needs both tools"
        description={`It joins the review to the semantic layer, and ${off} is not enabled here. Run: pf tool enable ${off.split(" ")[0]} ${group} ${project}`}
      />
    );
  }

  const c = data.counts ?? {};
  const columns = [
    {
      key: "name", header: "Semantic entity", sortable: true,
      render: (_: unknown, r: SemanticRow) => (
        <VStack gap="none">
          <Text className="pf-mono" weight="medium">{r.name}</Text>
          <Text size="xs" color="secondary" className="pf-mono">
            {r.schema}.{r.table}
          </Text>
        </VStack>
      ),
    },
    {
      key: "status", header: "Review", sortable: true,
      render: (_: unknown, r: SemanticRow) => (
        <VStack gap="none">
          <Verdict verdict={
            r.status === "moved" ? "changed"
              : r.status === "held" ? "clean"
              : r.status === "uncovered" ? "warning" : "unknown"
          } label={r.status} />
          <Text size="xs" color="secondary">
            {r.checks ? `${r.checks} check(s)` : "—"}
          </Text>
        </VStack>
      ),
    },
    {
      key: "row_count", header: "Rows", align: "right" as const,
      render: (_: unknown, r: SemanticRow) => {
        if (!r.row_count) return <Text color="secondary">—</Text>;
        const d = r.row_count.delta;
        return (
          <VStack gap="none" align="end">
            <Text className="pf-num"
                  color={d > 0 ? "error" : d < 0 ? "warning" : "secondary"}>
              {d > 0 ? "+" : ""}{d.toLocaleString()}
            </Text>
            <Text size="xs" color="secondary" className="pf-num">
              {r.row_count.base.toLocaleString()} → {r.row_count.curr.toLocaleString()}
            </Text>
          </VStack>
        );
      },
    },
    {
      key: "categories_drifted", header: "What moved",
      render: (_: unknown, r: SemanticRow) => {
        const bits: React.ReactNode[] = [];
        if (r.rows_added) bits.push(
          <Badge key="a" variant="error">+{r.rows_added} rows</Badge>);
        if (r.rows_removed) bits.push(
          <Badge key="r" variant="warning">−{r.rows_removed} rows</Badge>);
        for (const col of r.categories_drifted ?? []) {
          bits.push(<Badge key={col} variant="warning">{col} drift</Badge>);
        }
        return bits.length
          ? <HStack gap="xs" wrap>{bits}</HStack>
          : <Text color="secondary">—</Text>;
      },
    },
    {
      // The roles are the reason the join is worth making: they name what the
      // moved relation actually carries downstream. Capped so one wide mart
      // does not set the row height for the whole table.
      key: "roles", header: "Ontology roles",
      render: (_: unknown, r: SemanticRow) => {
        const all = r.roles ?? [];
        if (!all.length) return <Text color="secondary">—</Text>;
        return (
          <HStack gap="xs" wrap>
            {all.slice(0, 4).map(x => <Badge key={x}>{x}</Badge>)}
            {all.length > 4 && <span title={all.slice(4).join(", ")}><Badge>+{all.length - 4}</Badge></span>}
          </HStack>
        );
      },
    },
  ];

  return (
    <VStack gap="lg">
      <PageHeader
        title="Workspace"
        subtitle={`${data.catalog}.${data.schema} — the recorded diff, read against the semantic layer`}
      />

      <Grid columns={{ xs: 1, sm: 2, lg: 4 }} gap="md">
        <KpiCard label="Entities moved"
                 value={data.reviewed ? (c.moved ?? 0) : "—"}
                 delta={{ text: data.reviewed ? "semantic layer affected" : "nothing measured yet",
                          tone: data.reviewed && c.moved ? "down" : "flat" }} />
        <KpiCard label="Held" value={data.reviewed ? (c.held ?? 0) : "—"}
                 delta={{ text: "checked, nothing moved", tone: "flat" }} />
        <KpiCard label="Uncovered" value={data.reviewed ? (c.uncovered ?? 0) : "—"}
                 delta={{ text: "published with no check",
                          tone: c.uncovered ? "down" : "flat" }} />
        <KpiCard label="Baseline" value={data.has_baseline ? "captured" : "none"}
                 delta={{ text: data.has_baseline ? "diffs are real" : "pf tool recce baseline",
                          tone: "flat" }} />
      </Grid>

      <Card title="Semantic impact of the recorded diff"
            subtitle="Every published entity, against what the review measured on the model behind it">
        <div className="pf-scroll-x">
          <Table
            data={data.models}
            columns={columns}
            keyField="name"
            sortable
            emptyMessage="No MDL yet — run pf bootstrap."
          />
        </div>
        {(data.unpublished ?? []).length > 0 && (
          <Text size="sm" color="secondary" style={{ marginTop: 12 }}>
            Also reviewed, not published to the semantic layer:{" "}
            {data.unpublished.map(u => u.model).join(", ")}
          </Text>
        )}
      </Card>
    </VStack>
  );
}
