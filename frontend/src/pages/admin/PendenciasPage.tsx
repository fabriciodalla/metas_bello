import { CycleSelect } from "./CycleSelect";
import { useCycleOverview } from "./useCycleOverview";
import { Spinner } from "../../components/ui/Spinner";
import { EmptyState } from "../../components/ui/EmptyState";
import { PendingAllocationsTable, type PendingAllocationItem } from "../../components/PendingAllocationsTable";

export function PendenciasPage() {
  const { cycles, selectedCycleId, setSelectedCycleId, overview, loading } = useCycleOverview();

  const pendentes: PendingAllocationItem[] = overview
    .filter((a) => !a.distributed && a.quantity_kg > 0 && a.owner_node_level !== "VENDEDOR")
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
      {!loading && pendentes.length === 0 && <EmptyState>Nada pendente neste ciclo.</EmptyState>}
      {!loading && pendentes.length > 0 && <PendingAllocationsTable items={pendentes} />}
    </section>
  );
}
