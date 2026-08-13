import React from "react";
import ReactDOM from "react-dom/client";
import { ForgeProvider } from "wss3-forge";
import "wss3-forge/styles";
import "./theme.css";
import App from "./App";

/**
 * Theme follows the operator's system setting unless they have chosen one, and
 * the choice persists. The old page did the same thing; losing it in the port
 * would have been a regression nobody asked for.
 */
function Root() {
  const [mode, setMode] = React.useState<"light" | "dark">(() => {
    const saved = localStorage.getItem("pf-theme");
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  React.useEffect(() => {
    localStorage.setItem("pf-theme", mode);
    document.documentElement.dataset.theme = mode;
  }, [mode]);

  return (
    <ForgeProvider mode={mode}>
      <App mode={mode} onToggleTheme={() => setMode(m => (m === "dark" ? "light" : "dark"))} />
    </ForgeProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
