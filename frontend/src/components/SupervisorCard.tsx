import type { HierarchyNode } from "../api/types";
import { Badge } from "./ui/Badge";
import { MetricChip } from "./ui/MetricChip";
import { NumericKgInput } from "./ui/NumericKgInput";
import { ProgressBar } from "./ui/ProgressBar";

function formatKg(value: number): string {
  return `${Math.round(value).toLocaleString("pt-BR")} kg`;
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

function initials(nome: string): string {
  const parts = nome.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

interface Props {
  supervisor: HierarchyNode;
  subgroupNome: string;
  quantityKg: number | "";
  onChange?: (value: number | "") => void;
  metaTotalSupervisorKg: number;
  metaSupervisorGrupoKg: number;
  groupTotalKg: number;
  /** Reaproveitado também pela tela "Meta Vendedor" (mesmo componente, um nível abaixo na
   * hierarquia) — só o texto do primeiro indicador muda ("Meta do supervisor"/"Meta do vendedor"). */
  metaLabel?: string;
}

// Um card por pessoa no carrossel horizontal (Supervisor em "Meta Supervisor", Vendedor em "Meta
// Vendedor") — mostra só o subgrupo atualmente selecionado na lateral esquerda (nunca a lista
// inteira de subgrupos). `onChange` ausente = card em modo leitura (subgrupo já distribuído,
// editar de novo exige reabrir a alocação primeiro).
export function SupervisorCard({
  supervisor,
  subgroupNome,
  quantityKg,
  onChange,
  metaTotalSupervisorKg,
  metaSupervisorGrupoKg,
  groupTotalKg,
  metaLabel = "Meta do supervisor",
}: Props) {
  const readOnly = !onChange;
  const groupPercent = groupTotalKg > 0 ? (metaSupervisorGrupoKg / groupTotalKg) * 100 : 0;

  return (
    <article className={["sv-card", !supervisor.ativo ? "sv-card-inactive" : ""].filter(Boolean).join(" ")}>
      <div className="sv-card-header">
        <span className="sv-card-avatar" aria-hidden="true">
          {initials(supervisor.nome)}
        </span>
        <div className="sv-card-identity">
          <span className="sv-card-name">{toTitleCase(supervisor.nome)}</span>
          <Badge variant={supervisor.ativo ? "success" : "neutral"}>
            {supervisor.ativo ? "Ativo" : "Inativo"}
          </Badge>
        </div>
      </div>

      <div className="sv-card-metrics">
        <MetricChip
          className="sv-card-metric"
          size="lg"
          label={metaLabel}
          value={formatKg(metaTotalSupervisorKg)}
          valueTitle={formatKg(metaTotalSupervisorKg)}
        />
        <div className="sv-card-metric-divider" aria-hidden="true" />
        <MetricChip
          className="sv-card-metric"
          size="lg"
          label="Meta no grupo"
          value={formatKg(metaSupervisorGrupoKg)}
          valueTitle={formatKg(metaSupervisorGrupoKg)}
        />
      </div>
      <ProgressBar
        percent={groupPercent}
        variant={groupPercent > 100 ? "danger" : "success"}
        size="sm"
        label={`Progresso de ${toTitleCase(supervisor.nome)} no grupo selecionado`}
      />

      <div className="sv-card-row">
        <label className="sv-card-row-label" htmlFor={`sv-input-${supervisor.id}`}>
          {subgroupNome}
        </label>
        <NumericKgInput
          id={`sv-input-${supervisor.id}`}
          value={quantityKg}
          onChange={(value) => onChange?.(value)}
          disabled={readOnly}
          ariaLabel={`Meta definida para ${toTitleCase(supervisor.nome)} em ${subgroupNome}`}
        />
      </div>

      <div className="sv-card-footer">
        <div className="sv-card-footer-row">
          <span className="sv-card-footer-label">Total distribuído no grupo</span>
          <span className="sv-card-footer-value">{formatKg(metaSupervisorGrupoKg)}</span>
        </div>
        <ProgressBar percent={groupPercent} variant={groupPercent > 100 ? "danger" : "success"} size="sm" />
        <span className="sv-card-footer-label">{formatPct(groupPercent)}</span>
      </div>
    </article>
  );
}
