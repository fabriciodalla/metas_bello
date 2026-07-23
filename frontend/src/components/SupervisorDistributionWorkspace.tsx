import { Save } from "lucide-react";
import type { HierarchyNode } from "../api/types";
import { SupervisorCard } from "./SupervisorCard";
import { Alert } from "./ui/Alert";
import { Badge } from "./ui/Badge";
import { Button } from "./ui/Button";
import { EmptyState } from "./ui/EmptyState";
import { ProgressBar } from "./ui/ProgressBar";

function formatKg(value: number): string {
  return `${Math.round(value).toLocaleString("pt-BR")} kg`;
}

function formatPct(value: number): string {
  return `${Math.round(value)}%`;
}

export interface SupervisorWorkspaceRow {
  supervisor: HierarchyNode;
  quantityKg: number | "";
  onChange?: (value: number | "") => void;
  metaTotalSupervisorKg: number;
  metaSupervisorGrupoKg: number;
}

interface Props {
  subgroupNome: string;
  rows: SupervisorWorkspaceRow[];
  total: number;
  diff: number;
  editable: boolean;
  submitting: boolean;
  canSave: boolean;
  hasDraft: boolean;
  error: string | null;
  info: string | null;
  onSave: () => void;
  groupTotalKg: number;
  /** Reaproveitado também pela tela "Meta Vendedor" — só o texto muda entre os dois papéis. */
  title?: string;
  emptyRowsMessage?: string;
  cardMetaLabel?: string;
}

// Painel principal da tela "Meta Supervisor": um card horizontal por Supervisor, todos mostrando
// só o subgrupo selecionado na lista lateral, mais o resumo fixo do subgrupo abaixo do carrossel.
// `editable=false` só quando o subgrupo ATUALMENTE selecionado já foi distribuído (reabrir está
// fora do escopo desta tela) — o botão Salvar continua ativo mesmo assim, pois salva o grupo
// inteiro (todos os subgrupos com rascunho pronto), não só o que está visível no momento.
export function SupervisorDistributionWorkspace({
  subgroupNome,
  rows,
  total,
  diff,
  editable,
  submitting,
  canSave,
  hasDraft,
  error,
  info,
  onSave,
  groupTotalKg,
  title = "Distribuição para Supervisores",
  emptyRowsMessage = "Nenhum supervisor disponível para distribuição.",
  cardMetaLabel = "Meta do supervisor",
}: Props) {
  const metaSubgrupo = total + diff;
  const percentSubgrupo = metaSubgrupo > 0 ? (total / metaSubgrupo) * 100 : 0;
  const isOver = diff < 0;

  return (
    <div className="sv-workspace">
      <div className="sv-workspace-header">
        <div className="card-title-group">
          <h4>{title}</h4>
          {hasDraft && (
            <span className="unsaved-indicator">
              <span className="unsaved-dot" aria-hidden="true" />
              Alterações não salvas no grupo
            </span>
          )}
          {!editable && <Badge variant="success">Este subgrupo já foi salvo</Badge>}
        </div>
        <Button onClick={onSave} disabled={!canSave || submitting} aria-label="Salvar distribuição do grupo">
          <Save size={16} />
          {submitting ? "Salvando…" : "Salvar distribuição"}
        </Button>
      </div>

      <div className="sv-carousel-wrap">
        {rows.length === 0 ? (
          <EmptyState>{emptyRowsMessage}</EmptyState>
        ) : (
          <div className="sv-carousel">
            {rows.map((row) => (
              <SupervisorCard
                key={row.supervisor.id}
                supervisor={row.supervisor}
                subgroupNome={subgroupNome}
                quantityKg={row.quantityKg}
                onChange={row.onChange}
                metaTotalSupervisorKg={row.metaTotalSupervisorKg}
                metaSupervisorGrupoKg={row.metaSupervisorGrupoKg}
                groupTotalKg={groupTotalKg}
                metaLabel={cardMetaLabel}
              />
            ))}
          </div>
        )}
      </div>

      <div className="rdt-summary sv-sticky-summary">
        <div className="rdt-summary-block">
          <span className="rdt-summary-label">Total distribuído no subgrupo</span>
          <span className="rdt-summary-value rdt-summary-positive">{formatKg(total)}</span>
        </div>
        <div className="rdt-summary-bar">
          <ProgressBar percent={percentSubgrupo} variant={isOver ? "danger" : "success"} />
          <span>{formatPct(percentSubgrupo)}</span>
        </div>
        <div className="rdt-summary-block rdt-summary-block-end">
          <span className="rdt-summary-label">Restante no subgrupo</span>
          <span
            className={
              diff === 0
                ? "rdt-summary-value rdt-summary-positive"
                : isOver
                  ? "rdt-summary-value rdt-summary-danger"
                  : "rdt-summary-value rdt-summary-warning"
            }
          >
            {formatKg(Math.abs(diff))}
          </span>
        </div>
      </div>

      {isOver && (
        <Alert variant="danger">
          Distribuição acima da meta do subgrupo em {formatKg(-diff)}. Ajuste os valores para salvar.
        </Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}
      {info && <Alert variant="warning">{info}</Alert>}
    </div>
  );
}
