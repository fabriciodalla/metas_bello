import { Eraser, Save, Wand2 } from "lucide-react";
import type { GoalAllocation, HierarchyNode } from "../api/types";
import { LEVEL_LABELS, type Level } from "../pages/admin/constants";
import type { DistributionRowsBag } from "./useDistributionRows";
import { Alert } from "./ui/Alert";
import { Button } from "./ui/Button";
import { MetricChip } from "./ui/MetricChip";
import { NumericKgInput } from "./ui/NumericKgInput";
import { ProgressBar } from "./ui/ProgressBar";

// CONTEXT_LEVELS (useDistributionRows.ts) só habilita este componente pra GERENTE→Regional e
// Regional→Local — os únicos dois níveis de alvo direto que aparecem aqui.
const CHILD_LEVEL_PLURAL_LABELS: Partial<Record<Level, string>> = {
  REGIONAL: "coordenadores regionais",
  LOCAL: "coordenadores locais",
};

function formatKg(value: number): string {
  return `${Math.round(value).toLocaleString("pt-BR")} kg`;
}

function formatPct(value: number): string {
  return `${Math.round(value)}%`;
}

function toTitleCase(nome: string): string {
  return nome
    .trim()
    .split(/\s+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

interface Props {
  allocation: GoalAllocation;
  directChildren: HierarchyNode[];
  bag: DistributionRowsBag;
}

export function RegionalDistributionTable({ allocation, directChildren, bag }: Props) {
  const { rows, contextByNode, total, diff, error, submitting, hasDraft, updateRow, handleSubmit } = bag;

  const metaKg = allocation.quantity_kg;
  const percentDistributed = metaKg > 0 ? (total / metaKg) * 100 : 0;
  const isOver = diff < 0;
  const canSave = !submitting && diff === 0;
  const childLevelPlural = CHILD_LEVEL_PLURAL_LABELS[directChildren[0]?.level as Level] ?? "coordenadores";

  return (
    <div className="rdt">
      <div className="rdt-header">
        <div className="card-title-group">
          <h4>Distribuição para {childLevelPlural}</h4>
          {hasDraft && (
            <span className="unsaved-indicator">
              <span className="unsaved-dot" aria-hidden="true" />
              Alterações não salvas
            </span>
          )}
        </div>
        <Button onClick={() => void handleSubmit()} disabled={!canSave}>
          <Save size={16} />
          {submitting ? "Salvando…" : "Salvar distribuição"}
        </Button>
      </div>

      <div className="table-wrap">
        <table className="table rdt-table">
          <thead>
            <tr>
              <th>{LEVEL_LABELS[directChildren[0]?.level as Level] ?? "Coordenador"}</th>
              <th>Meta sugerida</th>
              <th>Meta definida</th>
              <th>% do grupo</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const node = directChildren.find((n) => n.id === row.ownerNodeId);
              const context = row.ownerNodeId !== "" ? contextByNode[row.ownerNodeId] : undefined;
              const suggestedKg = context?.suggested_kg ?? null;
              const suggestedPct = suggestedKg !== null && metaKg > 0 ? (suggestedKg / metaKg) * 100 : null;
              const currentKg = typeof row.quantityKg === "number" ? row.quantityKg : 0;
              const rowPct = metaKg > 0 && row.quantityKg !== "" ? (currentKg / metaKg) * 100 : 0;
              const canApplySuggestion = suggestedKg !== null && row.quantityKg !== suggestedKg;
              const canClear = row.quantityKg !== "";

              return (
                <tr key={row.key}>
                  <td data-label="">
                    <strong className="rdt-coordinator-name">{node ? toTitleCase(node.nome) : "—"}</strong>
                  </td>
                  <td data-label="Meta sugerida">
                    {suggestedKg !== null ? (
                      <div className="rdt-suggested">
                        <strong>{formatKg(suggestedKg)}</strong>
                        <span>{formatPct(suggestedPct ?? 0)}</span>
                      </div>
                    ) : (
                      <span className="dist-context-empty">Sem sugestão</span>
                    )}
                  </td>
                  <td data-label="Meta definida">
                    <NumericKgInput
                      value={row.quantityKg}
                      onChange={(value) => updateRow(row.key, { quantityKg: value })}
                      ariaLabel={`Meta definida para ${node?.nome ?? "coordenador"}`}
                    />
                  </td>
                  <td data-label="% do grupo">
                    <div className="rdt-pct">
                      <span>{formatPct(rowPct)}</span>
                      <ProgressBar percent={rowPct} size="sm" />
                    </div>
                  </td>
                  <td data-label="Ações">
                    <div className="rdt-actions">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="btn-icon"
                        disabled={!canApplySuggestion}
                        onClick={() => suggestedKg !== null && updateRow(row.key, { quantityKg: suggestedKg })}
                        aria-label={`Aplicar sugestão para ${node?.nome ?? "coordenador"}`}
                        title="Aplicar sugestão"
                      >
                        <Wand2 size={16} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="btn-icon"
                        disabled={!canClear}
                        onClick={() => updateRow(row.key, { quantityKg: "" })}
                        aria-label={`Limpar valor de ${node?.nome ?? "coordenador"}`}
                        title="Limpar"
                      >
                        <Eraser size={16} />
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="rdt-summary">
        <MetricChip label="Total distribuído" value={formatKg(total)} tone="success" size="xl" />
        <div className="rdt-summary-bar">
          <ProgressBar percent={percentDistributed} variant={isOver ? "danger" : "success"} />
          <span>{formatPct(percentDistributed)}</span>
        </div>
        <MetricChip
          className="rdt-summary-block-end"
          label="Restante do grupo"
          value={formatKg(Math.abs(diff))}
          size="xl"
          tone={diff === 0 ? "success" : isOver ? "danger" : "warning"}
        />
      </div>

      {isOver && (
        <Alert variant="danger">Distribuição acima da meta em {formatKg(-diff)}. Ajuste os valores para salvar.</Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}
    </div>
  );
}
