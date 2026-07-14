import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type {
  AllocationOverview,
  Cycle,
  HierarchyNode,
  ProductGroup,
  ProductSubgroup,
  SyncResult,
} from "../api/types";

function HierarchyTree({ nodes, parentId, depth }: { nodes: HierarchyNode[]; parentId: number | null; depth: number }) {
  const children = nodes.filter((n) => n.parent === parentId);
  if (children.length === 0) return null;
  return (
    <ul style={{ marginLeft: depth * 16 }}>
      {children.map((node) => (
        <li key={node.id}>
          {node.nome} <small>({node.level_display}{!node.ativo && " — inativo"})</small>
          <HierarchyTree nodes={nodes} parentId={node.id} depth={depth + 1} />
        </li>
      ))}
    </ul>
  );
}

function DistributionOverviewSection({ cycles }: { cycles: Cycle[] }) {
  const [selectedCycleId, setSelectedCycleId] = useState<number | null>(null);
  const [overview, setOverview] = useState<AllocationOverview[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  useEffect(() => {
    if (cycles.length === 0) return;
    const open = cycles.find((cycle) => cycle.status === "ABERTO");
    setSelectedCycleId(open?.id ?? cycles[0].id);
  }, [cycles]);

  useEffect(() => {
    if (selectedCycleId === null) return;
    setLoading(true);
    void api
      .get<AllocationOverview[]>(`/cycles/${selectedCycleId}/distribution-overview/`)
      .then(setOverview)
      .finally(() => setLoading(false));
  }, [selectedCycleId]);

  const pendingNonLeaf = overview.filter((a) => !a.distributed && a.owner_node_level !== "VENDEDOR");

  async function handleDownload() {
    if (selectedCycleId === null) return;
    setDownloadError(null);
    try {
      await api.download(`/cycles/${selectedCycleId}/export/`, `meta_${selectedCycleId}.csv`);
    } catch (error) {
      setDownloadError(error instanceof ApiError ? error.message : "Falha ao baixar o arquivo.");
    }
  }

  return (
    <section>
      <h2>Distribuição de metas</h2>
      <label>
        Ciclo:{" "}
        <select
          value={selectedCycleId ?? ""}
          onChange={(e) => setSelectedCycleId(Number(e.target.value))}
        >
          {cycles.map((cycle) => (
            <option key={cycle.id} value={cycle.id}>
              {String(cycle.mes).padStart(2, "0")}/{cycle.ano} ({cycle.status})
            </option>
          ))}
        </select>
      </label>{" "}
      <button type="button" onClick={() => void handleDownload()} disabled={selectedCycleId === null}>
        Baixar meta completa (CSV)
      </button>
      {downloadError && <p role="alert">{downloadError}</p>}

      {loading && <p>Carregando…</p>}

      <h3>Quem ainda não distribuiu ({pendingNonLeaf.length})</h3>
      {pendingNonLeaf.length === 0 && !loading && <p>Nada pendente neste ciclo.</p>}
      {pendingNonLeaf.length > 0 && (
        <ul>
          {pendingNonLeaf.map((a) => (
            <li key={a.id}>
              {a.owner_node_nome} ({a.owner_node_level}) — {a.quantity_kg} kg — usuário(s):{" "}
              {a.owner_node_usernames.length > 0 ? a.owner_node_usernames.join(", ") : "sem usuário vinculado"}
            </li>
          ))}
        </ul>
      )}

      <h3>Todas as alocações do ciclo ({overview.length})</h3>
      <table>
        <thead>
          <tr>
            <th>Nível</th>
            <th>Nó</th>
            <th>Usuário(s)</th>
            <th>Kg</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {overview.map((a) => (
            <tr key={a.id}>
              <td>{a.owner_node_level}</td>
              <td>{a.owner_node_nome}</td>
              <td>{a.owner_node_usernames.join(", ") || "—"}</td>
              <td>{a.quantity_kg}</td>
              <td>{a.distributed ? "distribuído" : "pendente"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function SyncDataSection() {
  const [syncing, setSyncing] = useState(false);
  const [result, setResult] = useState<SyncResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSync() {
    setSyncing(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.post<SyncResult>("/sales-history/sync/");
      setResult(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao sincronizar os dados.");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <section>
      <h2>Dados de histórico de vendas</h2>
      <p>
        Sincroniza o acumulado de vendas e a carteira de clientes do ERP (últimos 12 meses) e
        reconstrói a base usada na sugestão automática de metas. Rode antes de abrir a
        distribuição do ciclo.
      </p>
      <button type="button" onClick={() => void handleSync()} disabled={syncing}>
        {syncing ? "Sincronizando…" : "Sincronizar dados agora"}
      </button>
      {error && <p role="alert">{error}</p>}
      {result && (
        <p>
          Sincronizado desde {result.synced_since}: {result.accumulated_count} linha(s) de
          acumulado, {result.portfolio_count} cliente(s) na carteira, {result.baseline_count}{" "}
          linha(s) na base de distribuição.
        </p>
      )}
    </section>
  );
}

export function AdminPage() {
  const { user } = useAuth();
  const [nodes, setNodes] = useState<HierarchyNode[]>([]);
  const [groups, setGroups] = useState<ProductGroup[]>([]);
  const [subgroups, setSubgroups] = useState<ProductSubgroup[]>([]);
  const [cycles, setCycles] = useState<Cycle[]>([]);

  useEffect(() => {
    void api.get<HierarchyNode[]>("/hierarchy/nodes/").then(setNodes);
    void api.get<ProductGroup[]>("/catalog/groups/").then(setGroups);
    void api.get<ProductSubgroup[]>("/catalog/subgroups/").then(setSubgroups);
    void api.get<Cycle[]>("/cycles/").then(setCycles);
  }, []);

  return (
    <div className="page">
      <h1>Gestão do Administrador</h1>
      <p>
        Edição de hierarquia, catálogo e histórico de mudanças acontece no{" "}
        <a href="/admin/" target="_blank" rel="noreferrer">
          Django Admin
        </a>
        . Esta tela é só uma visão consolidada de leitura.
      </p>

      {user?.is_admin && (
        <>
          <SyncDataSection />
          <DistributionOverviewSection cycles={cycles} />
        </>
      )}

      <h2>Hierarquia</h2>
      <HierarchyTree nodes={nodes} parentId={null} depth={0} />

      <h2>Catálogo</h2>
      {groups.map((group) => (
        <div key={group.id}>
          <strong>{group.nome}</strong>
          <ul>
            {subgroups
              .filter((s) => s.group === group.id)
              .map((subgroup) => (
                <li key={subgroup.id}>{subgroup.nome}</li>
              ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
