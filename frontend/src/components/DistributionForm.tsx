import { ChevronDown, ChevronUp, Plus, TriangleAlert, X } from "lucide-react";
import { useState } from "react";
import type { GoalAllocation, HierarchyNode } from "../api/types";
import { NumericKgInput } from "./ui/NumericKgInput";
import { Sparkline } from "./Sparkline";
import { useDistributionRows } from "./useDistributionRows";
import { Alert } from "./ui/Alert";
import { Button } from "./ui/Button";

function formatKg(value: number): string {
  return `${Math.round(value).toLocaleString("pt-BR")} kg`;
}

function formatSignedPct(value: number): string {
  const sign = value >= 0 ? "+" : "-";
  return `${sign}${Math.abs(value).toFixed(1).replace(".", ",")}%`;
}

function pctDiff(current: number, reference: number | null): number | null {
  if (reference === null || reference <= 0) return null;
  return ((current - reference) / reference) * 100;
}

interface Props {
  allocation: GoalAllocation;
  directChildren: HierarchyNode[];
  onDistributed: () => void;
}

// Distribuição genérica (linhas livres, destino selecionável) usada pelo único nível sem tela
// dedicada — Supervisor→Vendedor, sem contexto histórico. Gerente→Regional e Regional→Local usam
// RegionalDistributionTable (renderizado em GroupCycleOverview); a quebra do Coordenador Local
// (grupo→subgrupo→supervisor) tem suas próprias telas, "Distribuir Produtos" e "Meta Supervisor".
export function DistributionForm({ allocation, directChildren, onDistributed }: Props) {
  const {
    showContext,
    rows,
    contextByNode,
    total,
    diff,
    error,
    submitting,
    updateRow,
    addRow,
    removeRow,
    distributeEvenly,
    handleSubmit,
  } = useDistributionRows(allocation, directChildren, onDistributed);

  const [expandedKey, setExpandedKey] = useState<string | null>(null);

  return (
    <div className="distribution-form">
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Destino</th>
              {showContext && <th>Contexto</th>}
              <th>Quantidade (kg)</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const context = row.ownerNodeId !== "" ? contextByNode[row.ownerNodeId] : undefined;
              const currentKg = typeof row.quantityKg === "number" ? row.quantityKg : 0;
              const yoy = row.quantityKg !== "" ? pctDiff(currentKg, context?.same_month_last_year_kg ?? null) : null;
              const vs3 = row.quantityKg !== "" ? pctDiff(currentKg, context?.last_3_months_avg_kg ?? null) : null;
              const liveSharePct = total > 0 ? (currentKg / total) * 100 : null;
              const isExpanded = expandedKey === row.key;

              return (
                <>
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
                    {showContext && (
                      <td>
                        {context ? (
                          <div className="dist-context-cell">
                            <div className="dist-context-line">
                              <span>Ano passado</span>
                              <strong>
                                {context.same_month_last_year_kg !== null
                                  ? formatKg(context.same_month_last_year_kg)
                                  : "—"}
                              </strong>
                              {yoy !== null && (
                                <span className={yoy >= 0 ? "dist-context-positive" : "dist-context-negative"}>
                                  {formatSignedPct(yoy)}
                                </span>
                              )}
                            </div>
                            <div className="dist-context-line">
                              <span>Últ. 3 meses</span>
                              <strong>
                                {context.last_3_months_avg_kg !== null ? formatKg(context.last_3_months_avg_kg) : "—"}
                              </strong>
                              {vs3 !== null && (
                                <span className={vs3 >= 0 ? "dist-context-positive" : "dist-context-negative"}>
                                  {formatSignedPct(vs3)}
                                </span>
                              )}
                            </div>
                            <div className="dist-context-line">
                              <span>Participação</span>
                              <strong>
                                {context.historical_share_pct !== null
                                  ? `${context.historical_share_pct.toFixed(0)}% hist.`
                                  : "—"}
                              </strong>
                              {liveSharePct !== null && <span>{liveSharePct.toFixed(0)}% agora</span>}
                            </div>
                            {context.suggested_kg !== null && (
                              <div className="dist-context-line">
                                <span>Sugestão</span>
                                <strong>{formatKg(context.suggested_kg)}</strong>
                              </div>
                            )}
                            {context.has_gap && (
                              <div className="dist-context-gap">
                                <TriangleAlert size={12} /> histórico incompleto
                              </div>
                            )}
                            <button
                              type="button"
                              className="dist-context-toggle"
                              onClick={() => setExpandedKey(isExpanded ? null : row.key)}
                            >
                              {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                              Histórico
                            </button>
                          </div>
                        ) : (
                          <span className="dist-context-empty">Sem histórico</span>
                        )}
                      </td>
                    )}
                    <td>
                      <NumericKgInput
                        value={row.quantityKg}
                        onChange={(value) => updateRow(row.key, { quantityKg: value })}
                        ariaLabel="Quantidade em kg"
                      />
                    </td>
                    <td>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="btn-icon"
                        onClick={() => removeRow(row.key)}
                        aria-label="Remover linha"
                      >
                        <X size={16} />
                      </Button>
                    </td>
                  </tr>
                  {showContext && isExpanded && context && (
                    <tr key={`${row.key}-detail`}>
                      <td colSpan={4} className="dist-context-detail">
                        <Sparkline history={context.history} />
                      </td>
                    </tr>
                  )}
                </>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="distribution-form-actions">
        <Button variant="outline" size="sm" onClick={addRow}>
          <Plus size={14} /> linha
        </Button>
        <Button variant="ghost" size="sm" onClick={distributeEvenly} disabled={rows.length === 0}>
          Distribuir igualmente
        </Button>
      </div>

      <div className="mt-4">
        <Alert variant={diff === 0 ? "success" : diff > 0 ? "warning" : "danger"}>
          {diff === 0
            ? `Fecha exatamente com ${allocation.quantity_kg} kg.`
            : diff > 0
              ? `Faltam ${diff} kg para fechar ${allocation.quantity_kg} kg.`
              : `Sobram ${-diff} kg além de ${allocation.quantity_kg} kg.`}
        </Alert>
      </div>

      {error && <Alert variant="danger">{error}</Alert>}

      <Button onClick={handleSubmit} disabled={submitting || diff !== 0}>
        {submitting ? "Distribuindo…" : "Distribuir"}
      </Button>
    </div>
  );
}
