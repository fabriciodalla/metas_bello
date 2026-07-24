import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api, ApiError } from "../../api/client";
import type { FeristaCoverage, HierarchyNode } from "../../api/types";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Modal } from "../../components/ui/Modal";

const MONTH_LABELS = [
  "Janeiro",
  "Fevereiro",
  "Março",
  "Abril",
  "Maio",
  "Junho",
  "Julho",
  "Agosto",
  "Setembro",
  "Outubro",
  "Novembro",
  "Dezembro",
];

function CoverageModal({
  coverage,
  vendedores,
  onClose,
  onSaved,
}: {
  coverage: FeristaCoverage | null;
  vendedores: HierarchyNode[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const now = new Date();
  const [externalName, setExternalName] = useState(coverage?.external_name ?? "");
  const [coveredNode, setCoveredNode] = useState<number | "">(coverage?.covered_node ?? "");
  const [ano, setAno] = useState(coverage?.ano ?? now.getFullYear());
  const [mes, setMes] = useState(coverage?.mes ?? now.getMonth() + 1);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = { external_name: externalName.trim().toUpperCase(), covered_node: coveredNode, ano, mes };
      if (coverage === null) {
        await api.post("/hierarchy/ferista-coverages/", payload);
      } else {
        await api.patch(`/hierarchy/ferista-coverages/${coverage.id}/`, payload);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao salvar a cobertura.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title={coverage === null ? "Nova cobertura de férias" : `Editando cobertura de ${coverage.external_name}`} onClose={onClose}>
      <form onSubmit={(e) => void handleSubmit(e)}>
        <div className="field">
          <label className="field-label" htmlFor="ferista-nome">
            Nome do ferista (como aparece no sistema de vendas)
          </label>
          <input
            id="ferista-nome"
            value={externalName}
            onChange={(e) => setExternalName(e.target.value)}
            required
            autoFocus
          />
        </div>
        <div className="field">
          <label className="field-label" htmlFor="ferista-cobrindo">
            Vendedor coberto
          </label>
          <select
            id="ferista-cobrindo"
            value={coveredNode}
            onChange={(e) => setCoveredNode(e.target.value ? Number(e.target.value) : "")}
            required
          >
            <option value="" disabled>
              Selecione…
            </option>
            {vendedores.map((v) => (
              <option key={v.id} value={v.id}>
                {v.nome}
              </option>
            ))}
          </select>
        </div>
        <div className="field-group">
          <div className="field">
            <label className="field-label" htmlFor="ferista-mes">
              Mês
            </label>
            <select id="ferista-mes" value={mes} onChange={(e) => setMes(Number(e.target.value))} required>
              {MONTH_LABELS.map((label, i) => (
                <option key={i + 1} value={i + 1}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label className="field-label" htmlFor="ferista-ano">
              Ano
            </label>
            <input
              id="ferista-ano"
              type="number"
              value={ano}
              onChange={(e) => setAno(Number(e.target.value))}
              required
            />
          </div>
        </div>
        {error && (
          <Alert variant="danger" role="alert">
            {error}
          </Alert>
        )}
        <div className="field-group">
          <Button type="submit" disabled={saving}>
            {saving ? "Salvando…" : coverage === null ? "Criar" : "Salvar"}
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function FeristaManager() {
  const [coverages, setCoverages] = useState<FeristaCoverage[]>([]);
  const [nodes, setNodes] = useState<HierarchyNode[]>([]);
  const [modal, setModal] = useState<FeristaCoverage | null | undefined>(undefined);
  const [nameFilter, setNameFilter] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);

  function reload() {
    void api.get<FeristaCoverage[]>("/hierarchy/ferista-coverages/").then(setCoverages);
    void api.get<HierarchyNode[]>("/hierarchy/nodes/").then(setNodes);
  }

  useEffect(reload, []);

  const vendedores = useMemo(
    () => nodes.filter((n) => n.level === "VENDEDOR" && n.ativo).sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR")),
    [nodes],
  );

  const filteredCoverages = useMemo(() => {
    const term = nameFilter.trim().toLowerCase();
    if (!term) return coverages;
    return coverages.filter(
      (c) => c.external_name.toLowerCase().includes(term) || c.covered_node_nome.toLowerCase().includes(term),
    );
  }, [coverages, nameFilter]);

  function handleSaved() {
    reload();
    setModal(undefined);
  }

  async function handleDelete(coverage: FeristaCoverage) {
    setDeleteError(null);
    try {
      await api.delete(`/hierarchy/ferista-coverages/${coverage.id}/`);
      reload();
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Falha ao excluir a cobertura.");
    }
  }

  return (
    <div>
      <Card
        title="Feristas"
        actions={
          <Button type="button" size="sm" onClick={() => setModal(null)}>
            <Plus size={14} /> Nova cobertura
          </Button>
        }
      >
        <p className="text-muted mt-0">
          Vendedor que cobre férias de outro vendedor num mês específico — o volume vendido nesse mês passa a
          contar pro histórico do vendedor coberto, não pra ninguém mais.
        </p>
        <div className="filter-bar">
          <div className="field-input-icon">
            <Search size={16} />
            <input
              type="search"
              placeholder="Buscar por nome…"
              value={nameFilter}
              onChange={(e) => setNameFilter(e.target.value)}
            />
          </div>
        </div>
        {deleteError && <Alert variant="danger">{deleteError}</Alert>}
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Ferista</th>
                <th>Cobrindo</th>
                <th>Mês/Ano</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filteredCoverages.length === 0 && (
                <tr>
                  <td colSpan={4} className="table-empty-cell">
                    Nenhuma cobertura cadastrada.
                  </td>
                </tr>
              )}
              {filteredCoverages.map((coverage) => (
                <tr key={coverage.id}>
                  <td>{coverage.external_name}</td>
                  <td>
                    <Badge variant="neutral">{coverage.covered_node_nome}</Badge>
                  </td>
                  <td>
                    {String(coverage.mes).padStart(2, "0")}/{coverage.ano}
                  </td>
                  <td>
                    <Button variant="ghost" size="sm" onClick={() => setModal(coverage)}>
                      <Pencil size={14} /> Editar
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => void handleDelete(coverage)}>
                      <Trash2 size={14} /> Excluir
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {modal !== undefined && (
        <CoverageModal coverage={modal} vendedores={vendedores} onClose={() => setModal(undefined)} onSaved={handleSaved} />
      )}
    </div>
  );
}
