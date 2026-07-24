import { Eraser, Package, Save, Target, Wand2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { GoalAllocation, SubgroupDistributionContext } from "../api/types";
import { Alert } from "./ui/Alert";
import { Button } from "./ui/Button";
import { MetricChip } from "./ui/MetricChip";
import { NumericKgInput } from "./ui/NumericKgInput";
import { ProgressBar } from "./ui/ProgressBar";
import { SummaryCard } from "./ui/SummaryCard";

function formatKg(value: number): string {
  return `${Math.round(value).toLocaleString("pt-BR")} kg`;
}

function formatPct(value: number): string {
  return `${Math.round(value)}%`;
}

function diffColorClass(diff: number): string {
  if (diff === 0) return "metric-chip-value-success";
  return diff > 0 ? "metric-chip-value-warning" : "metric-chip-value-danger";
}

interface SubgroupRow {
  subgroupId: number;
  subgroupNome: string;
  quantityKg: number | "";
}

interface Props {
  allocation: GoalAllocation;
  onSplit: () => void;
}

// Tela "Distribuir Produtos": o Coordenador Local quebra a meta GROUP recebida em subgrupos, com
// sugestão pré-preenchida (mesma lógica de tendência+sazonalidade, por subgrupo). Salva de
// verdade — a distribuição por Supervisor de cada subgrupo acontece depois, na tela "Meta
// Supervisor", sobre a alocação SUBGROUP criada aqui.
export function SubgroupSplitForm({ allocation, onSplit }: Props) {
  const [rows, setRows] = useState<SubgroupRow[]>([]);
  const [contextBySubgroup, setContextBySubgroup] = useState<Record<number, SubgroupDistributionContext>>({});
  const [prefilled, setPrefilled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    void api
      .get<SubgroupDistributionContext[]>(`/allocations/${allocation.id}/subgroup-distribution-context/`)
      .then((data) => {
        setContextBySubgroup(Object.fromEntries(data.map((ctx) => [ctx.subgroup_id, ctx])));
        setRows((current) =>
          current.length > 0
            ? current
            : [...data]
                .sort((a, b) => a.subgroup_nome.localeCompare(b.subgroup_nome, "pt-BR", { sensitivity: "base" }))
                .map((ctx) => ({
                  subgroupId: ctx.subgroup_id,
                  subgroupNome: ctx.subgroup_nome,
                  quantityKg: "",
                })),
        );
      })
      .catch(() => setContextBySubgroup({}))
      .finally(() => setLoading(false));
  }, [allocation.id]);

  useEffect(() => {
    if (prefilled || Object.keys(contextBySubgroup).length === 0) return;
    setRows((current) =>
      current.map((row) => {
        const suggested = contextBySubgroup[row.subgroupId]?.suggested_kg;
        return row.quantityKg === "" && suggested != null ? { ...row, quantityKg: suggested } : row;
      }),
    );
    setPrefilled(true);
  }, [contextBySubgroup, prefilled]);

  const total = rows.reduce((sum, row) => sum + (typeof row.quantityKg === "number" ? row.quantityKg : 0), 0);
  const diff = allocation.quantity_kg - total;
  const percentDistributed = allocation.quantity_kg > 0 ? (total / allocation.quantity_kg) * 100 : 0;
  const isOver = diff < 0;

  function updateRow(subgroupId: number, value: number | "") {
    setRows((current) =>
      current.map((row) => (row.subgroupId === subgroupId ? { ...row, quantityKg: value } : row)),
    );
  }

  async function handleSubmit() {
    setError(null);
    setSubmitting(true);
    try {
      await api.post(`/allocations/${allocation.id}/split-subgroups/`, {
        subgroups: rows.map((row) => ({
          subgroup_id: row.subgroupId,
          quantity_kg: typeof row.quantityKg === "number" ? row.quantityKg : 0,
        })),
      });
      onSplit();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao dividir por subgrupo.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading && rows.length === 0) {
    return <p className="ssw-loading">Carregando subgrupos…</p>;
  }

  if (rows.length === 0) {
    return <Alert variant="warning">Nenhum subgrupo cadastrado para este grupo.</Alert>;
  }

  const hasDraft = rows.some((row) => row.quantityKg !== "");
  const withMetaCount = rows.filter((row) => typeof row.quantityKg === "number" && row.quantityKg > 0).length;

  return (
    <div className="ssw-panel">
      <div className="summary-row">
        <SummaryCard icon={Target} label="META DO GRUPO" value={formatKg(allocation.quantity_kg)} />
        <SummaryCard
          icon={Package}
          label="SUBGRUPOS"
          value={`${withMetaCount}/${rows.length}`}
          caption="Subgrupos com metas"
        />
      </div>
      {/* Distribuído/Restante ao vivo já aparecem em rdt-summary, logo acima do botão Salvar —
          mostrar os mesmos dois números de novo aqui em cima seria repetir a mesma informação
          duas vezes na mesma tela com dois visuais diferentes. */}

      <div className="dp-workspace-card">
        <div className="rdt-header">
          <div className="card-title-group">
            <h4>Distribuição de Produtos</h4>
            {hasDraft && (
              <span className="unsaved-indicator">
                <span className="unsaved-dot" aria-hidden="true" />
                Alterações não salvas
              </span>
            )}
          </div>
          <Button onClick={() => void handleSubmit()} disabled={submitting || diff !== 0}>
            <Save size={16} />
            {submitting ? "Salvando…" : "Salvar Distribuição"}
          </Button>
        </div>

        <div className="table-wrap dp-table-scroll">
          <table className="table rdt-table">
            <thead>
              <tr>
                <th>Subgrupo</th>
                <th>Meta sugerida</th>
                <th>Meta definida</th>
                <th>% do grupo</th>
                <th>Diferença</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const context = contextBySubgroup[row.subgroupId];
                const suggestedKg = context?.suggested_kg ?? null;
                const suggestedPct =
                  suggestedKg !== null && allocation.quantity_kg > 0
                    ? (suggestedKg / allocation.quantity_kg) * 100
                    : null;
                const currentKg = typeof row.quantityKg === "number" ? row.quantityKg : 0;
                const rowPct =
                  allocation.quantity_kg > 0 && row.quantityKg !== ""
                    ? (currentKg / allocation.quantity_kg) * 100
                    : 0;
                const rowDiff = suggestedKg !== null ? currentKg - suggestedKg : null;
                const canApplySuggestion = suggestedKg !== null && row.quantityKg !== suggestedKg;
                const canClear = row.quantityKg !== "";

                return (
                  <tr key={row.subgroupId}>
                    <td data-label="">
                      <strong className="rdt-coordinator-name">{row.subgroupNome}</strong>
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
                        onChange={(value) => updateRow(row.subgroupId, value)}
                        ariaLabel={`Meta definida para o subgrupo ${row.subgroupNome}`}
                      />
                    </td>
                    <td data-label="% do grupo">
                      <div className="rdt-pct">
                        <span>{formatPct(rowPct)}</span>
                        <ProgressBar percent={rowPct} size="sm" />
                      </div>
                    </td>
                    <td data-label="Diferença">
                      {rowDiff !== null ? (
                        <strong className={diffColorClass(rowDiff)}>
                          {rowDiff === 0 ? "0 kg" : `${rowDiff > 0 ? "+" : "−"}${formatKg(Math.abs(rowDiff))}`}
                        </strong>
                      ) : (
                        <span className="dist-context-empty">—</span>
                      )}
                    </td>
                    <td data-label="Ações">
                      <div className="rdt-actions">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="btn-icon"
                          disabled={!canApplySuggestion}
                          onClick={() => suggestedKg !== null && updateRow(row.subgroupId, suggestedKg)}
                          aria-label={`Aplicar sugestão para ${row.subgroupNome}`}
                          title="Aplicar sugestão"
                        >
                          <Wand2 size={16} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="btn-icon"
                          disabled={!canClear}
                          onClick={() => updateRow(row.subgroupId, "")}
                          aria-label={`Limpar valor de ${row.subgroupNome}`}
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
      </div>

      {error && <Alert variant="danger">{error}</Alert>}
    </div>
  );
}
