import { Pencil, Plus, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import type { HierarchyNode, UserAccount } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { Badge } from "../../components/ui/Badge";
import { UserEditModal, displayName } from "./UserEditModal";

export function UserManager() {
  const [users, setUsers] = useState<UserAccount[]>([]);
  const [nodes, setNodes] = useState<HierarchyNode[]>([]);
  const [modalUser, setModalUser] = useState<UserAccount | null | undefined>(undefined);
  const [search, setSearch] = useState("");

  const filteredUsers = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return users;
    return users.filter(
      (user) =>
        displayName(user).toLowerCase().includes(term) ||
        user.username.toLowerCase().includes(term) ||
        user.email.toLowerCase().includes(term)
    );
  }, [users, search]);

  function reload() {
    void api.get<UserAccount[]>("/accounts/users/").then(setUsers);
    void api.get<HierarchyNode[]>("/hierarchy/nodes/").then(setNodes);
  }

  useEffect(reload, []);

  function closeModal() {
    setModalUser(undefined);
  }

  function handleSaved() {
    reload();
    closeModal();
  }

  return (
    <div>
      <Card
        title="Usuários"
        actions={
          <Button type="button" size="sm" onClick={() => setModalUser(null)}>
            <Plus size={14} /> Novo usuário
          </Button>
        }
      >
        <div className="filter-bar">
          <div className="field-input-icon">
            <Search size={16} />
            <input
              type="search"
              placeholder="Buscar por nome ou e-mail…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>E-mail</th>
                <th>Admin</th>
                <th>Ativo</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.length === 0 && (
                <tr>
                  <td colSpan={5} className="table-empty-cell">
                    Nenhum usuário encontrado.
                  </td>
                </tr>
              )}
              {filteredUsers.map((user) => (
                <tr key={user.id}>
                  <td>{displayName(user)}</td>
                  <td>{user.email}</td>
                  <td>
                    <Badge variant={user.is_admin ? "accent" : "neutral"}>
                      {user.is_admin ? "sim" : "não"}
                    </Badge>
                  </td>
                  <td>
                    <Badge variant={user.is_active ? "success" : "neutral"}>
                      {user.is_active ? "ativo" : "inativo"}
                    </Badge>
                  </td>
                  <td>
                    <Button variant="ghost" size="sm" onClick={() => setModalUser(user)}>
                      <Pencil size={14} /> Editar
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {modalUser !== undefined && (
        <UserEditModal
          user={modalUser}
          nodes={nodes}
          onClose={closeModal}
          onSaved={handleSaved}
          onChanged={reload}
        />
      )}
    </div>
  );
}
