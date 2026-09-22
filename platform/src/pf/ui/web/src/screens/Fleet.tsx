import React from "react";
import {
  Badge, Banner, Button, Card, EmptyState, Grid, HStack, KpiCard, PageHeader,
  Spinner, StatusBadge, Table, Text, VStack,
} from "wss3-forge";
import {
  Add20Regular, BuildingMultiple24Regular,
} from "@fluentui/react-icons";
import {
  api, type Fleet as FleetData, type FleetGroup, type FleetProject,
  type ProvisionOptions,
} from "../api";
import NewGroupDialog from "../components/NewGroupDialog";
import NewProjectDialog from "../components/NewProjectDialog";

/**
 * Every tenant this platform operates, and the two buttons that add one.
 *
 * `/api/tree` already answers "what may I select". This screen answers "what do
 * we operate", which is a different list: lifecycle, owner, tier and template
 * drift are the columns an operator works from, and none of them are needed to
 * populate a project picker.
 *
 * Grouped by family rather than shown as one flat table of projects. A group is
 * a real boundary in this platform — shared ontology instance, conformed
 * dimensions, one gate severity — and a flat list invites reading across one,
 * which is the assumption the router file exists to prevent.
 */
const LIFECYCLE_STATUS: Record<string, "active" | "pending" | "draft" | "inactive" | "error"> = {
  active: "active",
  provisioned: "pending",
  proposed: "draft",
  suspended: "inactive",
  offboarding: "pending",
  archived: "inactive",
};

/** A count, or the fact that nothing has measured it.
 *
 *  `null` is not zero. A green nought over a project no graph has been built for
 *  is a clean bill of health nobody issued, so the two render differently. */
function Count({ value }: { value: number | null }) {
  if (value === null) {
    return <Text size="sm" color="secondary">not built</Text>;
  }
  return <Text className="pf-num" size="sm">{value.toLocaleString()}</Text>;
}

function GroupCard({ group, onAddProject }: {
  group: FleetGroup;
  onAddProject: (group: string) => void;
}) {
  const columns = [
    {
      key: "name", header: "Project", sortable: true,
      render: (_: unknown, r: FleetProject) => (
        <VStack gap="none">
          <HStack gap="xs" align="center">
            <Text className="pf-mono" weight="medium">{r.name}</Text>
            {r.is_rollup && <Badge variant="info" size="sm">roll-up</Badge>}
          </HStack>
          <Text size="xs" color="secondary" className="pf-mono">{r.path}</Text>
        </VStack>
      ),
    },
    {
      key: "warehouse", header: "Warehouse", sortable: true,
      render: (_: unknown, r: FleetProject) =>
        r.warehouse
          ? <Badge>{r.warehouse}</Badge>
          : <Text size="sm" color="secondary">—</Text>,
    },
    {
      key: "models", header: "Models", align: "right" as const,
      render: (_: unknown, r: FleetProject) => <Count value={r.models} />,
    },
    {
      key: "sources", header: "Sources", align: "right" as const,
      render: (_: unknown, r: FleetProject) => <Count value={r.sources} />,
    },
    {
      key: "metrics", header: "Metrics", align: "right" as const,
      render: (_: unknown, r: FleetProject) => <Count value={r.metrics} />,
    },
    {
      key: "tests", header: "Tests", align: "right" as const,
      render: (_: unknown, r: FleetProject) => <Count value={r.tests} />,
    },
  ];

  const owner = group.owner_team || group.owner_contact;

  return (
    <Card
      title={group.display_name || group.name}
      subtitle={group.display_name ? group.name : undefined}
      action={{ label: "Add project", onClick: () => onAddProject(group.name) }}
    >
      <VStack gap="md">
        <HStack gap="xs" wrap align="center">
          <StatusBadge
            status={LIFECYCLE_STATUS[group.lifecycle ?? ""] ?? "draft"}
            label={group.lifecycle || "no manifest"}
          />
          {group.domain && <Badge variant="info">{group.domain}</Badge>}
          {group.tier === "critical" && <Badge variant="warning">critical</Badge>}
          {group.residency && <Badge>{group.residency}</Badge>}
          {owner
            ? <Text size="xs" color="secondary">{owner}</Text>
            : <Text size="xs" color="warning">no owner recorded</Text>}
          {group.behind_template && (
            <Badge variant="warning">
              template v{group.template_version} of v{group.template_version_current}
            </Badge>
          )}
        </HStack>

        {group.error && (
          <Banner variant="error" title="Manifest will not load">{group.error}</Banner>
        )}

        {group.projects.length === 0 ? (
          <EmptyState
            icon={<BuildingMultiple24Regular />}
            title="No projects yet"
            description="A group with no projects passes every gate in the repository by having nothing to fail."
            action={{ label: "Add project", onClick: () => onAddProject(group.name) }}
          />
        ) : (
          <div className="pf-scroll-x">
            <Table
              data={group.projects}
              columns={columns}
              keyField="name"
              sortable
              searchable={false}
              pagination={false}
              compact
            />
          </div>
        )}

        {group.classes.length > 0 && (
          <HStack gap="xs" wrap>
            <Text size="xs" color="secondary">Ontology:</Text>
            {group.classes.slice(0, 8).map(c => (
              <Badge key={c} size="sm">{c}</Badge>
            ))}
            {group.classes.length > 8 && (
              <Badge size="sm">+{group.classes.length - 8}</Badge>
            )}
          </HStack>
        )}
      </VStack>
    </Card>
  );
}

export default function Fleet({ onChanged }: { onChanged?: () => void }) {
  const [data, setData] = React.useState<FleetData | null>(null);
  const [options, setOptions] = React.useState<ProvisionOptions | null>(null);
  const [error, setError] = React.useState("");
  const [groupOpen, setGroupOpen] = React.useState(false);
  const [projectOpen, setProjectOpen] = React.useState(false);
  const [target, setTarget] = React.useState("");
  const [notice, setNotice] = React.useState("");

  const reload = React.useCallback(() => {
    api.get<FleetData>("/api/fleet").then(setData).catch(e => setError(e.message));
    api.get<ProvisionOptions>("/api/provision/options")
      .then(setOptions).catch(e => setError(e.message));
  }, []);

  React.useEffect(reload, [reload]);

  if (error) return <Text color="error">{error}</Text>;
  if (!data) return <Spinner />;

  const c = data.counts;

  return (
    <VStack gap="lg">
      <PageHeader
        title="Fleet"
        subtitle={`${c.groups} group(s), ${c.projects} project(s) — ${data.root}`}
        actions={
          <HStack gap="sm">
            <Button variant="secondary" onClick={() => setGroupOpen(true)}>
              <Add20Regular /> New group
            </Button>
            <Button
              onClick={() => { setTarget(""); setProjectOpen(true); }}
              disabled={c.groups === 0}
            >
              <Add20Regular /> New project
            </Button>
          </HStack>
        }
      />

      {notice && (
        <Banner variant="success" showCloseButton onClose={() => setNotice("")}>
          {notice}
        </Banner>
      )}

      <Grid columns={{ xs: 1, sm: 2, lg: 4 }} gap="md">
        <KpiCard label="Groups" value={c.groups}
                 delta={{ text: "families of sister companies", tone: "flat" }} />
        <KpiCard label="Projects" value={c.projects}
                 delta={{ text: "legal entities", tone: "flat" }} />
        <KpiCard label="Active" value={c.active}
                 delta={{ text: "loops run, gates are strict", tone: "flat" }} />
        <KpiCard label="Behind template" value={c.behind_template}
                 delta={{ text: c.behind_template ? "pf bootstrap --all" : "all current",
                          tone: c.behind_template ? "down" : "flat" }} />
      </Grid>

      {data.unmanaged.length > 0 && (
        <Banner variant="warning" title="Groups with no manifest">
          {data.unmanaged.join(", ")} — a directory under groups/ with no group.yaml
          has no owner, no lifecycle and no template version. `pf bootstrap` writes one.
        </Banner>
      )}

      {data.groups.length === 0 ? (
        <EmptyState
          icon={<BuildingMultiple24Regular />}
          title="No groups yet"
          description="A group is a family of sister companies sharing one ontology instance. Create one, then add the first entity to it."
          action={{ label: "New group", onClick: () => setGroupOpen(true) }}
        />
      ) : (
        data.groups.map(g => (
          <GroupCard key={g.name} group={g}
                     onAddProject={name => { setTarget(name); setProjectOpen(true); }} />
        ))
      )}

      <NewGroupDialog
        open={groupOpen}
        onClose={() => setGroupOpen(false)}
        options={options}
        onCreated={r => {
          setGroupOpen(false);
          setNotice(`Group ${r.group} created with ${r.file_count} files. Next: add its first entity.`);
          reload();
          onChanged?.();
        }}
      />

      <NewProjectDialog
        open={projectOpen}
        onClose={() => setProjectOpen(false)}
        options={options}
        fleet={data}
        initialGroup={target}
        onCreated={() => { reload(); onChanged?.(); }}
      />
    </VStack>
  );
}
