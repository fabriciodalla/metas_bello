import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { ChildAllocationInput, GoalAllocation, HierarchyNode, ProductSubgroup } from "../api/types";

interface Row {
  key: string;
  ownerNodeId: number | "";
  subgroupId: number | "";
  quantityKg: string;
}

function emptyRow(): Row {
  return { key: crypto.randomUUID(), ownerNodeId: "", subgroupId: "", quantityKg: "" };
}

interface Props {
  allocation: GoalAllocation;
  directChildren: HierarchyNode[];
  onDistributed: () => void;
}

export function DistributionForm({ allocation, directChildren, onDistributed }: Props) {
  const breaksToSubgroup = allocation.granularity === "GROUP" && allocation.owner_node_level === "LOCAL";

  const [rows, setRows] = useState<Row[]>(() =>
    directChildren.length > 0
      ? directChildren.map((node) => ({ ...emptyRow(), ownerNodeId: node.id }))
      : [emptyRow()],
  );
  const [subgroups, setSubgroups] = useState<ProductSubgroup[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (breaksToSubgroup && allocation.group) {
      void api
        .get<ProductSubgroup[]>(`/catalog/subgroups/?group=${allocation.group}`)
        .then(setSubgroups)
        .catch(() => setSubgroups([]));
    }
  }, [breaksToSubgroup, allocation.group]);

  const total = rows.reduce((sum, row) => sum + (Number(row.quantityKg) || 0), 0);
  const diff = allocation.quantity_kg - total;

  function updateRow(key: string, patch: Partial<Row>) {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }

  function addRow() {
    setRows((current) => [...current, emptyRow()]);
  }

  function removeRow(key: string) {
    setRows((current) => current.filter((row) => row.key !== key));
  }

  async function handleSubmit() {
    setError(null);

    if (rows.some((row) => row.ownerNodeId === "" || row.quantityKg === "")) {
      setError("Preencha o destino e a quantidade de todas as linhas.");
      return;
    }
    if (breaksToSubgroup && rows.some((row) => row.subgroupId === "")) {
      setError("Escolha o subgrupo de cada linha.");
      return;
    }

    const children: ChildAllocationInput[] = rows.map((row) => ({
      owner_node_id: row.ownerNodeId as number,
      quantity_kg: Number(row.quantityKg),
      granularity: breaksToSubgroup ? "SUBGROUP" : allocation.granularity,
      group_id: breaksToSubgroup ? null : allocation.group,
      subgroup_id: breaksToSubgroup ? (row.subgroupId as number) : allocation.subgroup,
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

  return (
    <div className="distribution-form">
      <table>
        <thead>
          <tr>
            <th>Destino</th>
            {breaksToSubgroup && <th>Subgrupo</th>}
            <th>Quantidade (kg)</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              <td>
                <select
                  value={row.ownerNodeId}
                  onChange={(e) => updateRow(row.key, { ownerNodeId: Number(e.target.value) || "" })}
                >
                  <option value="">Selecione…</option>
                  {directChildren.map((node) => (
                    <option key={node.id} value={node.id}>
                      {node.nome}
                    </option>
                  ))}
                </select>
              </td>
              {breaksToSubgroup && (
                <td>
                  <select
                    value={row.subgroupId}
                    onChange={(e) => updateRow(row.key, { subgroupId: Number(e.target.value) || "" })}
                  >
                    <option value="">Selecione…</option>
                    {subgroups.map((subgroup) => (
                      <option key={subgroup.id} value={subgroup.id}>
                        {subgroup.nome}
                      </option>
                    ))}
                  </select>
                </td>
              )}
              <td>
                <input
                  type="number"
                  min={0}
                  value={row.quantityKg}
                  onChange={(e) => updateRow(row.key, { quantityKg: e.target.value })}
                />
              </td>
              <td>
                <button type="button" onClick={() => removeRow(row.key)} aria-label="Remover linha">
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <button type="button" onClick={addRow}>
        + linha
      </button>

      <p className={diff === 0 ? "sum-ok" : "sum-diff"}>
        {diff === 0
          ? `Fecha exatamente com ${allocation.quantity_kg} kg.`
          : diff > 0
            ? `Faltam ${diff} kg para fechar ${allocation.quantity_kg} kg.`
            : `Sobram ${-diff} kg além de ${allocation.quantity_kg} kg.`}
      </p>

      {error && <p className="error">{error}</p>}

      <button type="button" onClick={handleSubmit} disabled={submitting || diff !== 0}>
        {submitting ? "Distribuindo…" : "Distribuir"}
      </button>
    </div>
  );
}
