"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, HierarchyTreeNode, HierarchyEvent } from "@/lib/api";

export default function HierarquiaAdminPage() {
  const [tree, setTree] = useState<HierarchyTreeNode[]>([]);
  const [events, setEvents] = useState<HierarchyEvent[]>([]);
  const [tab, setTab] = useState<"tree" | "events">("tree");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getTree(), api.getHierarchyEvents()])
      .then(([t, e]) => { setTree(t); setEvents(e); })
      .finally(() => setLoading(false));
  }, []);

  async function handleToggleActive(nodeId: number, currentActive: boolean) {
    await api.updateNode(nodeId, { is_active: !currentActive });
    const t = await api.getTree();
    setTree(t);
    const e = await api.getHierarchyEvents();
    setEvents(e);
  }

  return (
    <Shell>
      <h2 className="text-2xl font-bold mb-4">Hierarquia Comercial</h2>

      <div className="flex gap-2 mb-4">
        <button onClick={() => setTab("tree")} className={`px-3 py-1.5 rounded text-sm ${tab === "tree" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600"}`}>
          Arvore
        </button>
        <button onClick={() => setTab("events")} className={`px-3 py-1.5 rounded text-sm ${tab === "events" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600"}`}>
          Historico ({events.length})
        </button>
      </div>

      {loading ? <p className="text-gray-400">Carregando...</p> : tab === "tree" ? (
        <div className="bg-white rounded-xl border p-5">
          {tree.length === 0 ? (
            <p className="text-gray-400 text-center py-8">Nenhum no cadastrado</p>
          ) : tree.map((node) => <TreeNode key={node.id} node={node} depth={0} onToggle={handleToggleActive} />)}
        </div>
      ) : (
        <div className="bg-white rounded-xl border">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="px-4 py-3">Data</th>
                <th className="px-4 py-3">Pessoa</th>
                <th className="px-4 py-3">Evento</th>
                <th className="px-4 py-3">De</th>
                <th className="px-4 py-3">Para</th>
              </tr>
            </thead>
            <tbody>
              {events.map((ev) => (
                <tr key={ev.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-500">{ev.effective_on}</td>
                  <td className="px-4 py-2 font-medium">{ev.node_name}</td>
                  <td className="px-4 py-2">
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      ev.event_type === "ENTRADA" ? "bg-green-100 text-green-700" :
                      ev.event_type === "SAIDA" ? "bg-red-100 text-red-600" :
                      ev.event_type === "TRANSFERENCIA" ? "bg-blue-100 text-blue-700" :
                      ev.event_type === "INATIVACAO" ? "bg-orange-100 text-orange-700" :
                      "bg-gray-100 text-gray-600"
                    }`}>{ev.event_type}</span>
                  </td>
                  <td className="px-4 py-2 text-gray-500">{ev.old_parent_name || "-"}</td>
                  <td className="px-4 py-2 text-gray-500">{ev.new_parent_name || "-"}</td>
                </tr>
              ))}
              {events.length === 0 && (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Nenhum evento</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </Shell>
  );
}

function TreeNode({ node, depth, onToggle }: { node: HierarchyTreeNode; depth: number; onToggle: (id: number, active: boolean) => void }) {
  const [expanded, setExpanded] = useState(depth < 2);
  const has = node.children.length > 0;
  const colors: Record<number, string> = {
    1: "bg-blue-100 text-blue-700", 2: "bg-purple-100 text-purple-700",
    3: "bg-green-100 text-green-700", 4: "bg-yellow-100 text-yellow-700",
    5: "bg-orange-100 text-orange-700",
  };

  return (
    <div style={{ marginLeft: depth * 20 }}>
      <div className="flex items-center gap-2 py-1 hover:bg-gray-50 rounded px-2 group">
        {has ? (
          <button onClick={() => setExpanded(!expanded)} className="text-xs text-gray-400 w-4">{expanded ? "▼" : "▶"}</button>
        ) : <span className="w-4" />}
        <span className={`text-[10px] px-1.5 py-0.5 rounded ${colors[node.level.depth] || "bg-gray-100"}`}>{node.level.name}</span>
        <span className="text-sm">{node.name}</span>
        <span className="text-[10px] text-gray-400">{node.source_id}</span>
        {has && <span className="text-[10px] text-gray-400">({node.children.length})</span>}
        <button
          onClick={() => onToggle(node.id, node.is_active)}
          className="text-[10px] text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 ml-auto"
        >
          {node.is_active ? "inativar" : "reativar"}
        </button>
      </div>
      {expanded && has && node.children.map((c) => <TreeNode key={c.id} node={c} depth={depth + 1} onToggle={onToggle} />)}
    </div>
  );
}
