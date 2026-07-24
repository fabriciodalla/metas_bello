import { Pencil, Plus, Search } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api, ApiError } from "../../api/client";
import type { ProductGroup, ProductSubgroup } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Alert } from "../../components/ui/Alert";
import { Badge } from "../../components/ui/Badge";
import { Modal } from "../../components/ui/Modal";

type StatusFilter = "" | "ativo" | "inativo";

function matchesStatus(ativo: boolean, status: StatusFilter): boolean {
  if (status === "ativo") return ativo;
  if (status === "inativo") return !ativo;
  return true;
}

function GroupModal({
  group,
  onClose,
  onSaved,
}: {
  group: ProductGroup | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [nome, setNome] = useState(group?.nome ?? "");
  const [ativo, setAtivo] = useState(group?.ativo ?? true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (group === null) {
        await api.post("/catalog/groups/", { nome, ativo });
      } else {
        await api.patch(`/catalog/groups/${group.id}/`, { nome, ativo });
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao salvar o grupo.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title={group === null ? "Novo grupo" : `Editando: ${group.nome}`} onClose={onClose}>
      <form onSubmit={(e) => void handleSubmit(e)}>
        <div className="field">
          <label className="field-label" htmlFor="group-nome">
            Nome
          </label>
          <input id="group-nome" value={nome} onChange={(e) => setNome(e.target.value)} required autoFocus />
        </div>
        <label className="field-check">
          <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} />
          Ativo
        </label>
        {error && (
          <Alert variant="danger" role="alert">
            {error}
          </Alert>
        )}
        <div className="field-group">
          <Button type="submit" disabled={saving}>
            {saving ? "Salvando…" : group === null ? "Criar" : "Salvar"}
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function SubgroupModal({
  subgroup,
  groups,
  onClose,
  onSaved,
}: {
  subgroup: ProductSubgroup | null;
  groups: ProductGroup[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [nome, setNome] = useState(subgroup?.nome ?? "");
  const [groupId, setGroupId] = useState<number | "">(subgroup?.group ?? "");
  const [ativo, setAtivo] = useState(subgroup?.ativo ?? true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = { nome, group: groupId, ativo };
      if (subgroup === null) {
        await api.post("/catalog/subgroups/", payload);
      } else {
        await api.patch(`/catalog/subgroups/${subgroup.id}/`, payload);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao salvar o subgrupo.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title={subgroup === null ? "Novo subgrupo" : `Editando: ${subgroup.nome}`} onClose={onClose}>
      <form onSubmit={(e) => void handleSubmit(e)}>
        <div className="field-group">
          <div className="field">
            <label className="field-label" htmlFor="subgroup-nome">
              Nome
            </label>
            <input id="subgroup-nome" value={nome} onChange={(e) => setNome(e.target.value)} required autoFocus />
          </div>
          <div className="field">
            <label className="field-label" htmlFor="subgroup-group">
              Grupo
            </label>
            <select
              id="subgroup-group"
              value={groupId}
              onChange={(e) => setGroupId(e.target.value ? Number(e.target.value) : "")}
              required
            >
              <option value="" disabled>
                Grupo…
              </option>
              {groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.nome}
                </option>
              ))}
            </select>
          </div>
        </div>
        <label className="field-check">
          <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} />
          Ativo
        </label>
        {error && (
          <Alert variant="danger" role="alert">
            {error}
          </Alert>
        )}
        <div className="field-group">
          <Button type="submit" disabled={saving}>
            {saving ? "Salvando…" : subgroup === null ? "Criar" : "Salvar"}
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function CatalogManager() {
  const [groups, setGroups] = useState<ProductGroup[]>([]);
  const [subgroups, setSubgroups] = useState<ProductSubgroup[]>([]);
  const [groupModal, setGroupModal] = useState<ProductGroup | null | undefined>(undefined);
  const [subgroupModal, setSubgroupModal] = useState<ProductSubgroup | null | undefined>(undefined);

  const [groupNameFilter, setGroupNameFilter] = useState("");
  const [groupStatusFilter, setGroupStatusFilter] = useState<StatusFilter>("");

  const [subgroupNameFilter, setSubgroupNameFilter] = useState("");
  const [subgroupStatusFilter, setSubgroupStatusFilter] = useState<StatusFilter>("");
  const [subgroupGroupFilter, setSubgroupGroupFilter] = useState<number | "">("");

  function reload() {
    void api.get<ProductGroup[]>("/catalog/groups/").then(setGroups);
    void api.get<ProductSubgroup[]>("/catalog/subgroups/").then(setSubgroups);
  }

  useEffect(reload, []);

  const filteredGroups = useMemo(() => {
    const term = groupNameFilter.trim().toLowerCase();
    return groups.filter(
      (group) => group.nome.toLowerCase().includes(term) && matchesStatus(group.ativo, groupStatusFilter)
    );
  }, [groups, groupNameFilter, groupStatusFilter]);

  const filteredSubgroups = useMemo(() => {
    const term = subgroupNameFilter.trim().toLowerCase();
    return subgroups.filter(
      (subgroup) =>
        subgroup.nome.toLowerCase().includes(term) &&
        matchesStatus(subgroup.ativo, subgroupStatusFilter) &&
        (subgroupGroupFilter === "" || subgroup.group === subgroupGroupFilter)
    );
  }, [subgroups, subgroupNameFilter, subgroupStatusFilter, subgroupGroupFilter]);

  function handleGroupSaved() {
    reload();
    setGroupModal(undefined);
  }

  function handleSubgroupSaved() {
    reload();
    setSubgroupModal(undefined);
  }

  return (
    <div>
      <Card
        title="Grupos"
        actions={
          <Button type="button" size="sm" onClick={() => setGroupModal(null)}>
            <Plus size={14} /> Novo grupo
          </Button>
        }
      >
        <div className="filter-bar">
          <div className="field-input-icon">
            <Search size={16} />
            <input
              type="search"
              placeholder="Buscar por nome…"
              value={groupNameFilter}
              onChange={(e) => setGroupNameFilter(e.target.value)}
            />
          </div>
          <select value={groupStatusFilter} onChange={(e) => setGroupStatusFilter(e.target.value as StatusFilter)}>
            <option value="">Status: todos</option>
            <option value="ativo">Ativo</option>
            <option value="inativo">Inativo</option>
          </select>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filteredGroups.length === 0 && (
                <tr>
                  <td colSpan={3} className="table-empty-cell">
                    Nenhum grupo encontrado.
                  </td>
                </tr>
              )}
              {filteredGroups.map((group) => (
                <tr key={group.id}>
                  <td>{group.nome}</td>
                  <td>
                    <Badge variant={group.ativo ? "success" : "neutral"}>
                      {group.ativo ? "ativo" : "inativo"}
                    </Badge>
                  </td>
                  <td>
                    <Button variant="ghost" size="sm" onClick={() => setGroupModal(group)}>
                      <Pencil size={14} /> Editar
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title="Subgrupos"
        actions={
          <Button type="button" size="sm" onClick={() => setSubgroupModal(null)}>
            <Plus size={14} /> Novo subgrupo
          </Button>
        }
      >
        <div className="filter-bar">
          <div className="field-input-icon">
            <Search size={16} />
            <input
              type="search"
              placeholder="Buscar por nome…"
              value={subgroupNameFilter}
              onChange={(e) => setSubgroupNameFilter(e.target.value)}
            />
          </div>
          <select
            value={subgroupStatusFilter}
            onChange={(e) => setSubgroupStatusFilter(e.target.value as StatusFilter)}
          >
            <option value="">Status: todos</option>
            <option value="ativo">Ativo</option>
            <option value="inativo">Inativo</option>
          </select>
          <select
            value={subgroupGroupFilter}
            onChange={(e) => setSubgroupGroupFilter(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">Grupo: todos</option>
            {groups.map((group) => (
              <option key={group.id} value={group.id}>
                {group.nome}
              </option>
            ))}
          </select>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Grupo</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filteredSubgroups.length === 0 && (
                <tr>
                  <td colSpan={4} className="table-empty-cell">
                    Nenhum subgrupo encontrado.
                  </td>
                </tr>
              )}
              {filteredSubgroups.map((subgroup) => (
                <tr key={subgroup.id}>
                  <td>{subgroup.nome}</td>
                  <td>{groups.find((g) => g.id === subgroup.group)?.nome ?? "?"}</td>
                  <td>
                    <Badge variant={subgroup.ativo ? "success" : "neutral"}>
                      {subgroup.ativo ? "ativo" : "inativo"}
                    </Badge>
                  </td>
                  <td>
                    <Button variant="ghost" size="sm" onClick={() => setSubgroupModal(subgroup)}>
                      <Pencil size={14} /> Editar
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {groupModal !== undefined && (
        <GroupModal group={groupModal} onClose={() => setGroupModal(undefined)} onSaved={handleGroupSaved} />
      )}
      {subgroupModal !== undefined && (
        <SubgroupModal
          subgroup={subgroupModal}
          groups={groups}
          onClose={() => setSubgroupModal(undefined)}
          onSaved={handleSubgroupSaved}
        />
      )}
    </div>
  );
}
