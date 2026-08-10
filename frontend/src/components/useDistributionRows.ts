import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { ChildAllocationInput, ChildDistributionContext, GoalAllocation, HierarchyNode } from "../api/types";

export interface DistributionRow {
  key: string;
  ownerNodeId: number | "";
  quantityKg: number | "";
}

function emptyRow(): DistributionRow {
  return { key: crypto.randomUUID(), ownerNodeId: "", quantityKg: "" };
}

// Contexto histórico por alvo existe pra Gerente→Local e Meta Supervisor (a
// alocação SUBGROUP dona = Local, criada por "Distribuir Produtos", distribuída aqui pros
// Supervisores) — nos demais níveis (Supervisor→Vendedor) a distribuição segue só manual.
export const CONTEXT_LEVELS = new Set(["GERENTE", "LOCAL"]);

export function useDistributionRows(
  allocation: GoalAllocation,
  directChildren: HierarchyNode[],
  onDistributed: () => void,
) {
  const showContext = CONTEXT_LEVELS.has(allocation.owner_node_level);

  const [rows, setRows] = useState<DistributionRow[]>(() =>
    directChildren.length > 0
      ? directChildren.map((node) => ({ ...emptyRow(), ownerNodeId: node.id }))
      : [emptyRow()],
  );
  const [contextByNode, setContextByNode] = useState<Record<number, ChildDistributionContext>>({});
  const [prefilled, setPrefilled] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!showContext) return;
    void api
      .get<ChildDistributionContext[]>(`/allocations/${allocation.id}/distribution-context/`)
      .then((data) => {
        setContextByNode(Object.fromEntries(data.map((ctx) => [ctx.owner_node_id, ctx])));
      })
      .catch(() => setContextByNode({}));
  }, [showContext, allocation.id]);

  // A sugestão AUTO (quando existe pro nível) só pré-preenche linhas ainda intocadas, uma única
  // vez ao chegar; segue 100% editável depois disso.
  useEffect(() => {
    if (prefilled || Object.keys(contextByNode).length === 0) return;
    setRows((current) =>
      current.map((row) => {
        if (row.quantityKg !== "" || row.ownerNodeId === "") return row;
        const suggested = contextByNode[row.ownerNodeId]?.suggested_kg;
        return suggested != null ? { ...row, quantityKg: suggested } : row;
      }),
    );
    setPrefilled(true);
  }, [contextByNode, prefilled]);

  const total = rows.reduce((sum, row) => sum + (typeof row.quantityKg === "number" ? row.quantityKg : 0), 0);
  const diff = allocation.quantity_kg - total;

  function updateRow(key: string, patch: Partial<DistributionRow>) {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }

  function addRow() {
    setRows((current) => [...current, emptyRow()]);
  }

  function removeRow(key: string) {
    setRows((current) => current.filter((row) => row.key !== key));
  }

  function distributeEvenly() {
    const n = rows.length;
    if (n === 0) return;
    const base = Math.floor(allocation.quantity_kg / n);
    const remainder = allocation.quantity_kg - base * n;
    setRows((current) => current.map((row, i) => ({ ...row, quantityKg: base + (i < remainder ? 1 : 0) })));
  }

  async function handleSubmit() {
    setError(null);

    if (rows.some((row) => row.ownerNodeId === "" || row.quantityKg === "")) {
      setError("Preencha o destino e a quantidade de todas as linhas.");
      return;
    }

    const children: ChildAllocationInput[] = rows.map((row) => ({
      owner_node_id: row.ownerNodeId as number,
      quantity_kg: row.quantityKg as number,
      granularity: allocation.granularity,
      group_id: allocation.group,
      subgroup_id: allocation.subgroup,
      product_id: allocation.product,
    }));

    setSubmitting(true);
    try {
      await api.post(`/allocations/${allocation.id}/distribute/`, { children });
      onDistributed();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao distribuir.");
    } finally {
      setSubmitting(false);
    }
  }

  const hasDraft = rows.some((row) => row.quantityKg !== "");

  return {
    showContext,
    rows,
    contextByNode,
    total,
    diff,
    error,
    submitting,
    hasDraft,
    updateRow,
    addRow,
    removeRow,
    distributeEvenly,
    handleSubmit,
  };
}

export type DistributionRowsBag = ReturnType<typeof useDistributionRows>;
