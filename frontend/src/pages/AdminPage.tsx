import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { HierarchyNode, ProductGroup, ProductSubgroup } from "../api/types";

function HierarchyTree({ nodes, parentId, depth }: { nodes: HierarchyNode[]; parentId: number | null; depth: number }) {
  const children = nodes.filter((n) => n.parent === parentId);
  if (children.length === 0) return null;
  return (
    <ul style={{ marginLeft: depth * 16 }}>
      {children.map((node) => (
        <li key={node.id}>
          {node.nome} <small>({node.level_display}{!node.ativo && " — inativo"})</small>
          <HierarchyTree nodes={nodes} parentId={node.id} depth={depth + 1} />
        </li>
      ))}
    </ul>
  );
}

export function AdminPage() {
  const [nodes, setNodes] = useState<HierarchyNode[]>([]);
  const [groups, setGroups] = useState<ProductGroup[]>([]);
  const [subgroups, setSubgroups] = useState<ProductSubgroup[]>([]);

  useEffect(() => {
    void api.get<HierarchyNode[]>("/hierarchy/nodes/").then(setNodes);
    void api.get<ProductGroup[]>("/catalog/groups/").then(setGroups);
    void api.get<ProductSubgroup[]>("/catalog/subgroups/").then(setSubgroups);
  }, []);

  return (
    <div className="page">
      <h1>Gestão do Administrador</h1>
      <p>
        Edição de hierarquia, catálogo e histórico de mudanças acontece no{" "}
        <a href="/admin/" target="_blank" rel="noreferrer">
          Django Admin
        </a>
        . Esta tela é só uma visão consolidada de leitura.
      </p>

      <h2>Hierarquia</h2>
      <HierarchyTree nodes={nodes} parentId={null} depth={0} />

      <h2>Catálogo</h2>
      {groups.map((group) => (
        <div key={group.id}>
          <strong>{group.nome}</strong>
          <ul>
            {subgroups
              .filter((s) => s.group === group.id)
              .map((subgroup) => (
                <li key={subgroup.id}>{subgroup.nome}</li>
              ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
