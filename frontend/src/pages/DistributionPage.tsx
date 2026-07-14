import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { Cycle, GoalAllocation, HierarchyNode } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { DistributionForm } from "../components/DistributionForm";

export function DistributionPage() {
  const { user } = useAuth();
  const [cycles, setCycles] = useState<Cycle[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState<number | null>(null);
  const [allocations, setAllocations] = useState<GoalAllocation[]>([]);
  const [nodes, setNodes] = useState<HierarchyNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    void api.get<Cycle[]>("/cycles/").then((data) => {
      setCycles(data);
      const open = data.find((cycle) => cycle.status === "ABERTO");
      setSelectedCycleId(open?.id ?? data[0]?.id ?? null);
    });
    void api.get<HierarchyNode[]>("/hierarchy/nodes/").then(setNodes);
  }, []);

  useEffect(() => {
    if (selectedCycleId === null) return;
    setLoading(true);
    void api
      .get<GoalAllocation[]>(`/allocations/?cycle=${selectedCycleId}`)
      .then(setAllocations)
      .finally(() => setLoading(false));
  }, [selectedCycleId]);

  const myNodeId = user?.hierarchy_node?.id ?? null;

  const pending = useMemo(
    () => allocations.filter((a) => a.owner_node === myNodeId && !a.distributed),
    [allocations, myNodeId],
  );
  const done = useMemo(
    () => allocations.filter((a) => a.owner_node === myNodeId && a.distributed),
    [allocations, myNodeId],
  );

  function refresh() {
    if (selectedCycleId === null) return;
    void api.get<GoalAllocation[]>(`/allocations/?cycle=${selectedCycleId}`).then(setAllocations);
    setExpandedId(null);
  }

  return (
    <div className="page">
      <h1>Distribuição de metas</h1>

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
      </label>

      {loading && <p>Carregando…</p>}

      <h2>Para distribuir ({pending.length})</h2>
      {pending.length === 0 && !loading && <p>Nada pendente no seu nível para este ciclo.</p>}
      {pending.map((allocation) => {
        const directChildren = nodes.filter((n) => n.parent === allocation.owner_node);
        return (
          <div className="allocation-card" key={allocation.id}>
            <button type="button" onClick={() => setExpandedId(expandedId === allocation.id ? null : allocation.id)}>
              {allocation.quantity_kg} kg — {allocation.granularity}
              {expandedId === allocation.id ? " ▲" : " ▼"}
            </button>
            {expandedId === allocation.id && (
              <DistributionForm
                allocation={allocation}
                directChildren={directChildren}
                onDistributed={refresh}
              />
            )}
          </div>
        );
      })}

      <h2>Já distribuído ({done.length})</h2>
      <ul>
        {done.map((allocation) => (
          <li key={allocation.id}>
            {allocation.quantity_kg} kg — {allocation.granularity}
          </li>
        ))}
      </ul>
    </div>
  );
}
