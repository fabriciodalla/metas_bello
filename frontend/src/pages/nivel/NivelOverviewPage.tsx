import { useMemo } from "react";
import { CycleSelect } from "../admin/CycleSelect";
import { useAuth } from "../../auth/AuthContext";
import { useCycleAllocations } from "./useCycleAllocations";
import { StatRow, StatTile } from "../../components/ui/StatTile";
import { Spinner } from "../../components/ui/Spinner";
import { EmptyState } from "../../components/ui/EmptyState";
import { Card } from "../../components/ui/Card";
import { AllocationStatusTable, type AllocationStatusItem } from "../../components/AllocationStatusTable";

export function NivelOverviewPage() {
  const { user } = useAuth();
  const { cycles, selectedCycleId, setSelectedCycleId, allocations, loading } = useCycleAllocations();

  const myNodeIds = useMemo(() => new Set(user?.hierarchy_nodes.map((n) => n.id) ?? []), [user]);

  const totalKg = allocations
    .filter((a) => myNodeIds.has(a.owner_node))
    .reduce((sum, a) => sum + a.quantity_kg, 0);
  const kgNoVendedor = allocations
    .filter((a) => a.owner_node_level === "VENDEDOR")
    .reduce((sum, a) => sum + a.quantity_kg, 0);
  const percentualNaPonta = totalKg > 0 ? Math.round((kgNoVendedor / totalKg) * 100) : 0;

  const subordinados: AllocationStatusItem[] = allocations
    .filter((a) => a.quantity_kg > 0 && a.owner_node_level !== "VENDEDOR" && !myNodeIds.has(a.owner_node))
    .map((a) => ({
      id: a.id,
      ownerNodeId: a.owner_node,
      ownerNodeUsernames: a.owner_node_usernames,
      ownerNodeLevel: a.owner_node_level,
      parentAllocationId: a.parent_allocation,
      groupNome: a.group_nome,
      subgroupNome: a.subgroup_nome,
      quantityKg: a.quantity_kg,
      distributed: a.distributed,
      receivedAt: a.created_at,
      distributedAt: a.updated_at,
    }));

  const subordinadosPendentesCount = subordinados.filter((a) => !a.distributed).length;

  return (
    <section>
      <CycleSelect cycles={cycles} value={selectedCycleId} onChange={setSelectedCycleId} />

      {loading && <Spinner />}
      {!loading && allocations.length === 0 && (
        <EmptyState>Nenhuma alocação no seu ramo neste ciclo.</EmptyState>
      )}
      {!loading && allocations.length > 0 && (
        <>
          <StatRow>
            <StatTile value={`${totalKg} kg`} label="Sua meta neste ciclo" />
            <StatTile value={`${percentualNaPonta}%`} label="Já chegou ao Vendedor" />
            <StatTile value={subordinadosPendentesCount} label="Subordinados pendentes" />
          </StatRow>

          <Card title="Distribuição dos seus subordinados">
            {subordinados.length === 0 ? (
              <EmptyState>Nenhum subordinado com meta disponível neste ciclo.</EmptyState>
            ) : (
              <AllocationStatusTable items={subordinados} />
            )}
          </Card>
        </>
      )}
    </section>
  );
}
