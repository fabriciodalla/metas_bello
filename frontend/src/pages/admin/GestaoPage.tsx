import { useState } from "react";
import { CatalogManager } from "./CatalogManager";
import { FeristaManager } from "./FeristaManager";
import { HierarchyManager } from "./HierarchyManager";
import { UserManager } from "./UserManager";

const TABS = ["Hierarquia", "Usuários", "Catálogo", "Feristas"] as const;
type Tab = (typeof TABS)[number];

export function GestaoPage() {
  const [tab, setTab] = useState<Tab>("Hierarquia");

  return (
    <section>
      <div className="tabs">
        {TABS.map((t) => (
          <button key={t} type="button" className={t === tab ? "active" : ""} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>
      {tab === "Hierarquia" && <HierarchyManager />}
      {tab === "Usuários" && <UserManager />}
      {tab === "Catálogo" && <CatalogManager />}
      {tab === "Feristas" && <FeristaManager />}
    </section>
  );
}
