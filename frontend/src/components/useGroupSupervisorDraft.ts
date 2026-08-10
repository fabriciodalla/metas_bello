import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { ChildAllocationInput, ChildDistributionContext, GoalAllocation, HierarchyNode } from "../api/types";

export type SubgroupDraftRow = Record<number, number | "">; // supervisorId -> quantityKg

// Distribuição em lote pra tela "Meta Supervisor": ao contrário de `useDistributionRows` (usado em
// Gerente→Local, uma alocação por vez), aqui um Coordenador Local pode ter
// dezenas de subgrupos no mesmo grupo — exigir "Salvar" a cada um seria repetitivo. O rascunho de
// TODOS os subgrupos do grupo selecionado fica vivo ao trocar de seleção na lateral; só é
// descartado ao trocar de grupo/ciclo (com aviso — ver MetaSupervisorPage) ou depois de salvo. Cada
// subgrupo continua persistido pelo mesmo endpoint POST /allocations/{id}/distribute/ já usado nas
// outras telas, só a orquestração (uma chamada por subgrupo pronto) muda.
export function useGroupSupervisorDraft(groupId: number | null, supervisors: HierarchyNode[]) {
  const [draft, setDraft] = useState<Record<number, SubgroupDraftRow>>({});
  const [contextBySubgroup, setContextBySubgroup] = useState<
    Record<number, Record<number, ChildDistributionContext>>
  >({});
  const [, setLoadedIds] = useState<Set<number>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    setDraft({});
    setContextBySubgroup({});
    setLoadedIds(new Set());
    setError(null);
    setInfo(null);
  }, [groupId]);

  // Chamado quando um subgrupo é selecionado pela primeira vez: cria a linha em branco (uma por
  // supervisor) e busca a sugestão histórica (mesmo endpoint de distribution-context), sem
  // recarregar nada dos subgrupos já visitados nesta sessão de edição do grupo.
  const ensureLoaded = useCallback(
    (allocationId: number) => {
      setDraft((prev) => {
        if (prev[allocationId]) return prev;
        const row: SubgroupDraftRow = {};
        for (const supervisor of supervisors) row[supervisor.id] = "";
        return { ...prev, [allocationId]: row };
      });

      setLoadedIds((prev) => {
        if (prev.has(allocationId)) return prev;
        void api
          .get<ChildDistributionContext[]>(`/allocations/${allocationId}/distribution-context/`)
          .then((data) => {
            const byNode = Object.fromEntries(data.map((ctx) => [ctx.owner_node_id, ctx]));
            setContextBySubgroup((current) => ({ ...current, [allocationId]: byNode }));
            setDraft((current) => {
              const row = current[allocationId];
              if (!row) return current;
              let changed = false;
              const updated = { ...row };
              for (const supervisor of supervisors) {
                const suggested = byNode[supervisor.id]?.suggested_kg;
                if (updated[supervisor.id] === "" && suggested != null) {
                  updated[supervisor.id] = suggested;
                  changed = true;
                }
              }
              return changed ? { ...current, [allocationId]: updated } : current;
            });
          })
          .catch(() => {});
        const next = new Set(prev);
        next.add(allocationId);
        return next;
      });
    },
    [supervisors],
  );

  function updateCell(allocationId: number, supervisorId: number, value: number | "") {
    setDraft((prev) => ({
      ...prev,
      [allocationId]: { ...(prev[allocationId] ?? {}), [supervisorId]: value },
    }));
  }

  function rowValue(allocationId: number, supervisorId: number): number | "" {
    return draft[allocationId]?.[supervisorId] ?? "";
  }

  function totalFor(allocationId: number): number {
    const row = draft[allocationId];
    if (!row) return 0;
    return Object.values(row).reduce<number>((sum, v) => sum + (typeof v === "number" ? v : 0), 0);
  }

  function hasDraftFor(allocationId: number): boolean {
    const row = draft[allocationId];
    return row ? Object.values(row).some((v) => v !== "") : false;
  }

  function hasAnyDraft(allocations: GoalAllocation[]): boolean {
    return allocations.some((a) => hasDraftFor(a.id));
  }

  // Salva de uma vez todo subgrupo tocado nesta sessão que já fecha exatamente com a meta —
  // subgrupos ainda incompletos ficam como estão (rascunho preservado, nada é descartado) e
  // aparecem no aviso informativo em vez de bloquear quem já terminou os outros.
  async function saveGroup(
    allocations: GoalAllocation[],
    nomeOf: (a: GoalAllocation) => string,
    onSaved: (saved: GoalAllocation[]) => void,
  ) {
    setError(null);
    setInfo(null);

    const touched = allocations.filter((a) => !a.distributed && hasDraftFor(a.id));
    const ready = touched.filter((a) => a.quantity_kg - totalFor(a.id) === 0);
    const pending = touched.filter((a) => a.quantity_kg - totalFor(a.id) !== 0);

    if (ready.length === 0) {
      setError(
        pending.length > 0
          ? `Ajuste a diferença para zero antes de salvar: ${pending.map(nomeOf).join(", ")}.`
          : "Nenhuma alteração para salvar.",
      );
      return;
    }

    setSubmitting(true);
    const saved: GoalAllocation[] = [];
    const failures: string[] = [];
    for (const allocation of ready) {
      const row = draft[allocation.id] ?? {};
      const children: ChildAllocationInput[] = supervisors.map((supervisor) => ({
        owner_node_id: supervisor.id,
        quantity_kg: typeof row[supervisor.id] === "number" ? (row[supervisor.id] as number) : 0,
        granularity: allocation.granularity,
        group_id: allocation.group,
        subgroup_id: allocation.subgroup,
        product_id: allocation.product,
      }));
      try {
        await api.post(`/allocations/${allocation.id}/distribute/`, { children });
        saved.push(allocation);
      } catch (err) {
        failures.push(`${nomeOf(allocation)}${err instanceof ApiError ? ` (${err.message})` : ""}`);
      }
    }
    setSubmitting(false);

    if (saved.length > 0) {
      setDraft((prev) => {
        const next = { ...prev };
        for (const allocation of saved) delete next[allocation.id];
        return next;
      });
    }

    const notes: string[] = [];
    if (pending.length > 0) notes.push(`ainda com diferença pendente: ${pending.map(nomeOf).join(", ")}`);
    if (failures.length > 0) notes.push(`falha ao salvar: ${failures.join(", ")}`);
    if (notes.length > 0) setInfo(notes.join(" — "));

    if (saved.length > 0) onSaved(saved);
  }

  return {
    hasDraftFor,
    hasAnyDraft,
    rowValue,
    updateCell,
    totalFor,
    ensureLoaded,
    contextBySubgroup,
    submitting,
    error,
    info,
    saveGroup,
  };
}
