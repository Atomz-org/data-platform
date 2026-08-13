import React from "react";
import {
  Badge, Card, Grid, KpiCard, PageHeader, SegmentedControl, Spinner, Table,
  Text, VStack,
} from "wss3-forge";
import { api, type RecceCheck } from "../api";
import { Verdict, type VerdictKind } from "../components/Verdict";

const VERDICT_KIND: Record<string, VerdictKind> = {
  changed: "changed", clean: "clean", not_run: "warning", errored: "unknown",
};

/**
 * What the review actually found, check by check.
 *
 * This existed only inside Recce's own server before, which meant a project
 * whose server was not running showed a review with no findings in it — and a
 * count of seventeen checks with no way to see what any of them said. The
 * detail is read from the recorded state, so it agrees with the run that
 * produced it rather than recomputing and disagreeing.
 */
export default function Review({ group, project }: { group: string; project: string }) {
  const [checks, setChecks] = React.useState<RecceCheck[] | null>(null);
  const [counts, setCounts] = React.useState<Record<string, number>>({});
  const [filter, setFilter] = React.useState("all");
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    setChecks(null);
    setError("");
    api.get<{ checks: RecceCheck[]; counts: Record<string, number> }>(
      "/api/tools/recce/checks", { group, project })
      .then(r => { setChecks(r.checks); setCounts(r.counts ?? {}); })
      .catch(e => setError(e.message));
  }, [group, project]);

  if (error) return <Text color="error">{error}</Text>;
  if (!checks) return <Spinner />;

  const rows = filter === "all" ? checks : checks.filter(c => c.verdict === filter);

  const columns = [
    {
      key: "verdict", header: "Verdict", width: 130, sortable: true,
      render: (_: unknown, c: RecceCheck) => (
        <Verdict verdict={VERDICT_KIND[c.verdict] ?? "unknown"} label={c.verdict.replace("_", " ")} />
      ),
    },
    {
      key: "name", header: "Check", sortable: true,
      render: (_: unknown, c: RecceCheck) => (
        <VStack gap="none">
          <Text weight="medium" size="sm">{c.name}</Text>
          {c.description && (
            <Text size="xs" color="secondary">{c.description}</Text>
          )}
        </VStack>
      ),
    },
    {
      key: "type", header: "Kind", width: 140,
      render: (_: unknown, c: RecceCheck) => <Badge>{c.type || "—"}</Badge>,
    },
    {
      // The finding itself. Without this column the table is a list of names
      // and the operator still has to open another tool to learn anything.
      key: "detail", header: "What it found",
      render: (_: unknown, c: RecceCheck) => (
        <Text size="sm" color={c.verdict === "changed" ? "primary" : "secondary"}>
          {c.detail || "—"}
        </Text>
      ),
    },
  ];

  return (
    <VStack gap="lg">
      <PageHeader
        title="Review"
        subtitle={`${group}/${project} — every recorded check and its verdict`}
      />

      <Grid columns={{ xs: 2, lg: 4 }} gap="md">
        <KpiCard label="Changed" value={counts.changed ?? 0}
                 delta={{ text: "the review found a difference", tone: "flat" }} />
        <KpiCard label="Clean" value={counts.clean ?? 0}
                 delta={{ text: "ran, found nothing", tone: "flat" }} />
        <KpiCard label="Not run" value={counts.not_run ?? 0}
                 delta={{ text: "recorded but never executed", tone: "flat" }} />
        <KpiCard label="Errored" value={counts.errored ?? 0}
                 delta={{ text: "failed to complete", tone: "flat" }} />
      </Grid>

      <Card
        title="Checks"
        subtitle="Findings first — read down until the differences run out"
      >
        <div style={{ marginBottom: 12 }}>
          <SegmentedControl
            value={filter}
            onChange={setFilter}
            options={[
              { id: "all", label: `All ${checks.length}` },
              { id: "changed", label: `Changed ${counts.changed ?? 0}` },
              { id: "clean", label: `Clean ${counts.clean ?? 0}` },
              { id: "not_run", label: `Not run ${counts.not_run ?? 0}` },
            ]}
          />
        </div>
        <div className="pf-scroll-x">
          <Table
            data={rows}
            columns={columns}
            keyField="name"
            sortable
            emptyMessage="No review recorded — run pf tool recce run."
          />
        </div>
      </Card>
    </VStack>
  );
}
