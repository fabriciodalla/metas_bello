import { useMemo } from "react";
import { CycleSelect } from "../admin/CycleSelect";
import { useAuth } from "../../auth/AuthContext";
import { useCycleAllocations } from "./useCycleAllocations";
import { Spinner } from "../../components/ui/Spinner";
import { EmptyState } from "../../components/ui/EmptyState";
import { PendingAllocationsTable, type PendingAllocationItem } from "../../components/PendingAllocationsTable";

export function NivelPendenciasPage() {
  const { user } = useAuth();
  const { cycles, selectedCycleId, setSelectedCycleId, allocations, loading } = useCycleAllocations();

  const myNodeIds = useMemo(() => new Set(user?.hierarchy_nodes.map((n) => n.id) ?? []), [user]);

  const pendentes: PendingAllocationItem[] = allocations
    .filter(
      (a) =>
        !a.distributed &&
        a.quantity_kg > 0 &&
        a.owner_node_level !== "VENDEDOR" &&
        !myNodeIds.has(a.owner_node),
    )
    .map((a) => ({
      id: a.id,
      ownerNodeId: a.owner_node,
      ownerNodeUsernames: a.owner_node_usernames,
      ownerNodeLevel: a.owner_node_level,
      groupNome: a.group_nome,
      subgroupNome: a.subgroup_nome,
      quantityKg: a.quantity_kg,
      createdAt: a.created_at,
    }));

  return (
    <section>
      <CycleSelect cycles={cycles} value={selectedCycleId} onChange={setSelectedCycleId} />

      {loading && <Spinner />}
      {!loading && pendentes.length === 0 && (
        <EmptyState>Nenhum subordinado pendente neste ciclo.</EmptyState>
      )}
      {!loading && pendentes.length > 0 && <PendingAllocationsTable items={pendentes} />}
    </section>
  );
}
