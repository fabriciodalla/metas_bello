"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Shell from "@/components/Shell";
import StatusBadge from "@/components/StatusBadge";
import { api, GoalCycle, DashboardData, HierarchyStatus } from "@/lib/api";

export default function DashboardPage() {
  const [cycles, setCycles] = useState<GoalCycle[]>([]);
  const [data, setData] = useState<DashboardData | null>(null);
  const [selectedCycle, setSelectedCycle] = useState<number | null>(null);
  const [userRole, setUserRole] = useState("");

  useEffect(() => {
    api.me().then((u) => setUserRole(u.role)).catch(() => {});
    api.getCycles().then((c) => {
      setCycles(c);
      if (c.length > 0) setSelectedCycle(c[0].id);
    }).catch(console.error);
  }, []);

  useEffect(() => {
    if (selectedCycle && (userRole === "GERENTE" || userRole === "ADMINISTRADOR")) {
      api.getGerenciaDashboard(selectedCycle).then(setData).catch(() => {});
    }
  }, [selectedCycle, userRole]);

  const active = cycles.filter((c) => c.status === "RASCUNHO" || c.status === "EM_DISTRIBUICAO");
  const totalKg = cycles.reduce((s, c) => s + Number(c.total_kg), 0);
  const totalSellers = cycles.reduce((s, c) => s + c.sellers_count, 0);

  // Status grouped by level, exclude gerente (depth=1)
  const statusByLevel: Record<string, HierarchyStatus[]> = {};
  if (data) {
    for (const s of data.hierarchy_status) {
      if (s.depth <= 1) continue;
      if (!statusByLevel[s.level_name]) statusByLevel[s.level_name] = [];
      statusByLevel[s.level_name].push(s);
    }
  }

  const levelEntries = Object.entries(statusByLevel)
    .sort(([, a], [, b]) => (a[0]?.depth || 0) - (b[0]?.depth || 0));

  return (
    <Shell>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        {cycles.length > 1 && (
          <select
            value={selectedCycle ?? ""}
            onChange={(e) => setSelectedCycle(Number(e.target.value))}
            className="border rounded-lg px-3 py-2 text-sm"
          >
            {cycles.map((c) => (
              <option key={c.id} value={c.id}>
                {String(c.month).padStart(2, "0")}/{c.year}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Stat label="Ciclos ativos" value={active.length} color="blue" />
        <Stat label="Total kg distribuido" value={totalKg.toLocaleString("pt-BR")} color="green" />
        <Stat label="Metas de vendedores" value={totalSellers} color="purple" />
      </div>

      {/* Status da Distribuicao — tabela transposta */}
      {data && levelEntries.length > 0 && (
        <div className="bg-white rounded-xl border mb-8">
          <div className="px-5 py-4 border-b">
            <h3 className="font-semibold">Status da Distribuicao</h3>
            <p className="text-xs text-gray-400">
              Ciclo {data.targets.cycle_label} — Quem ja distribuiu e quem falta
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b bg-gray-50">
                  <th className="px-5 py-3 w-56">Nome</th>
                  <th className="px-5 py-3 w-40">Nivel</th>
                  <th className="px-5 py-3">Superior</th>
                  <th className="px-5 py-3 text-right">Recebido (kg)</th>
                  <th className="px-5 py-3 text-right">Distribuido (kg)</th>
                  <th className="px-5 py-3 text-center w-24">Status</th>
                </tr>
              </thead>
              {levelEntries.map(([levelName, nodes]) => {
                const done = nodes.filter((n) => n.has_distributed).length;
                return (
                  <tbody key={levelName}>
                    <tr className="bg-gray-50 border-b">
                      <td colSpan={5} className="px-5 py-2 text-xs font-semibold text-gray-500 uppercase">
                        {levelName}
                      </td>
                      <td className="px-5 py-2 text-center">
                        <span className={`text-xs font-bold ${
                          done === nodes.length ? "text-green-600" : done > 0 ? "text-yellow-600" : "text-gray-400"
                        }`}>
                          {done}/{nodes.length}
                        </span>
                      </td>
                    </tr>
                    {nodes.map((n) => (
                      <tr key={n.node_id} className="border-b last:border-0 hover:bg-gray-50">
                        <td className="px-5 py-2 font-medium">{n.node_name}</td>
                        <td className="px-5 py-2 text-gray-400 text-xs">{n.level_name}</td>
                        <td className="px-5 py-2 text-gray-500 text-xs">{n.parent_name}</td>
                        <td className="px-5 py-2 text-right">
                          {Number(n.total_received) > 0
                            ? Number(n.total_received).toLocaleString("pt-BR")
                            : <span className="text-gray-300">—</span>}
                        </td>
                        <td className="px-5 py-2 text-right">
                          {Number(n.total_distributed) > 0
                            ? Number(n.total_distributed).toLocaleString("pt-BR")
                            : <span className="text-gray-300">—</span>}
                        </td>
                        <td className="px-5 py-2 text-center">
                          {n.has_distributed ? (
                            <span className="inline-block w-2.5 h-2.5 rounded-full bg-green-500" title="Distribuiu" />
                          ) : Number(n.total_received) > 0 ? (
                            <span className="inline-block w-2.5 h-2.5 rounded-full bg-yellow-400" title="Recebeu, nao distribuiu" />
                          ) : (
                            <span className="inline-block w-2.5 h-2.5 rounded-full bg-gray-300" title="Aguardando" />
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                );
              })}
            </table>
          </div>
        </div>
      )}

      {/* Ciclos recentes */}
      <div className="bg-white rounded-xl border">
        <div className="px-5 py-4 border-b flex justify-between items-center">
          <h3 className="font-semibold">Ciclos recentes</h3>
          <Link href="/ciclos" className="text-sm text-blue-600 hover:underline">Ver todos</Link>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="px-5 py-3">Periodo</th>
              <th className="px-5 py-3 text-right">Total kg</th>
              <th className="px-5 py-3 text-right">Vendedores</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {cycles.slice(0, 6).map((c) => (
              <tr key={c.id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-5 py-3 font-medium">{String(c.month).padStart(2, "0")}/{c.year}</td>
                <td className="px-5 py-3 text-right">{Number(c.total_kg).toLocaleString("pt-BR")}</td>
                <td className="px-5 py-3 text-right">{c.sellers_count}</td>
                <td className="px-5 py-3"><StatusBadge status={c.status} /></td>
                <td className="px-5 py-3">
                  <Link href={`/ciclos/${c.id}`} className="text-blue-600 hover:underline text-sm">Detalhar</Link>
                </td>
              </tr>
            ))}
            {cycles.length === 0 && (
              <tr><td colSpan={5} className="px-5 py-8 text-center text-gray-400">Nenhum ciclo</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}

function Stat({ label, value, color }: { label: string; value: string | number; color: string }) {
  const c: Record<string, string> = {
    blue: "border-blue-200 bg-blue-50", green: "border-green-200 bg-green-50",
    purple: "border-purple-200 bg-purple-50",
  };
  return (
    <div className={`rounded-xl border p-4 ${c[color] || ""}`}>
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}
