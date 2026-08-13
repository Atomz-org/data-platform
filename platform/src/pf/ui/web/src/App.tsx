import React from "react";
import {
  AppSidebar, Box, Button, HStack, Select, Spinner, Text, VStack,
} from "wss3-forge";
import {
  Board20Regular, DataTrending20Regular, Molecule20Regular,
  ShieldCheckmark20Regular, WeatherMoon20Regular, WeatherSunny20Regular,
} from "@fluentui/react-icons";
import { api, type Tree } from "./api";
import Workspace from "./screens/Workspace";
import Review from "./screens/Review";
import Semantics from "./screens/Semantics";
import Governance from "./screens/Governance";

/**
 * Shell shape is taken from the shadcn admin template (see the vendor registry):
 * a persistent sidebar grouped by intent, a topbar carrying the one piece of
 * state every screen depends on, and a content column that scrolls on its own.
 *
 * The project selector lives in the topbar rather than on each screen because
 * every screen below is scoped to one project, and repeating the control per
 * screen is how two of them end up disagreeing about which project is active.
 */
const SECTIONS = [
  {
    title: "Change",
    items: [
      { id: "workspace", icon: <Board20Regular />, label: "Workspace" },
      { id: "review", icon: <ShieldCheckmark20Regular />, label: "Review" },
    ],
  },
  {
    title: "Semantics",
    items: [
      { id: "semantics", icon: <DataTrending20Regular />, label: "Semantic layer" },
      { id: "governance", icon: <Molecule20Regular />, label: "Governance" },
    ],
  },
];

export default function App({ mode, onToggleTheme }: {
  mode: "light" | "dark";
  onToggleTheme: () => void;
}) {
  const [tab, setTab] = React.useState("workspace");
  const [tree, setTree] = React.useState<Tree | null>(null);
  const [error, setError] = React.useState("");
  const [active, setActive] = React.useState<{ group: string; project: string } | null>(null);

  React.useEffect(() => {
    api.get<Tree>("/api/tree")
      .then(t => {
        setTree(t);
        const all = t.groups.flatMap(g => g.projects.map(p => ({
          group: g.name, project: p.name,
        })));
        // Restore the last project. Every screen is scoped to one, so landing
        // on whichever happens to sort first means re-selecting on every visit.
        const saved = localStorage.getItem("pf-project");
        const match = all.find(a => `${a.group}/${a.project}` === saved);
        const first = match ?? all[0];
        if (first) setActive(first);
      })
      .catch(e => setError(e.message));
  }, []);

  React.useEffect(() => {
    if (active) localStorage.setItem("pf-project", `${active.group}/${active.project}`);
  }, [active]);

  const options = (tree?.groups ?? []).flatMap(g =>
    g.projects.map(p => ({ value: `${g.name}/${p.name}`, label: `${g.name}/${p.name}` })));

  return (
    <HStack gap="none" style={{ height: "100vh", alignItems: "stretch" }}>
      <AppSidebar
        mode="inline"
        sections={SECTIONS}
        value={tab}
        onNavigate={setTab}
        collapsible
        density="compact"
        logo={<Text weight="semibold">Data Platform</Text>}
        footerContent={
          <Text size="xs" color="secondary" className="pf-mono">
            {tree?.root ?? ""}
          </Text>
        }
      />

      <VStack gap="none" style={{ flex: 1, minWidth: 0, overflow: "hidden" }}>
        <HStack
          justify="between"
          align="center"
          px="lg"
          py="md"
          style={{ borderBottom: "1px solid var(--color-border)", flex: "none" }}
        >
          <HStack gap="md" align="center">
            <Select
              value={active ? `${active.group}/${active.project}` : ""}
              onChange={(v: string) => {
                const [group, project] = v.split("/");
                setActive({ group, project });
              }}
              options={options}
              placeholder="Select a project"
            />
          </HStack>
          <Button variant="ghost" size="sm" onClick={onToggleTheme}
                  aria-label="Toggle colour theme">
            {mode === "dark" ? <WeatherSunny20Regular /> : <WeatherMoon20Regular />}
          </Button>
        </HStack>

        <Box style={{ flex: 1, minHeight: 0, overflowY: "auto" }} p="lg">
          {error && <Text color="error">{error}</Text>}
          {!tree && !error && <Spinner />}
          {active && tab === "workspace" && <Workspace {...active} />}
          {active && tab === "review" && <Review {...active} />}
          {active && tab === "semantics" && <Semantics {...active} />}
          {tab === "governance" && <Governance group={active?.group ?? ""} />}
        </Box>
      </VStack>
    </HStack>
  );
}
