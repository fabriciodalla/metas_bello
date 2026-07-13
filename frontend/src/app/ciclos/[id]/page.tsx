"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Shell from "@/components/Shell";
import StatusBadge from "@/components/StatusBadge";
import { api, GoalCycle, GoalSummary } from "@/lib/api";

export default function CycleDetailPage() {
  const params = useParams();
  const cycleId = Number(params.id);
  const [cycle, setCycle] = useState<GoalCycle | null>(null);
  const [summaries, setSummaries] = useState<GoalSummary[]>([]);
  const [nodeId, setNodeId] = useState<number | null>(null);

  useEffect(() => {
    api.getCycle(cycleId).then(setCycle);
    api.me().then((user) => {
      if (user.scope_node_id) {
        setNodeId(user.scope_node_id);
        api.getGoalSummary(cycleId, user.scope_node_id).then(setSummaries);
      }
    });
  }, [cycleId]);

  if (!cycle) return <Shell><p className="text-gray-400">Carregando...</p></Shell>;

  return (
    <Shell>
      <div className="flex justify-between items-center mb-6">
        <div>
          <Link href="/ciclos" className="text-sm text-gray-400 hover:text-gray-600">Ciclos</Link>
          <h2 className="text-2xl font-bold">Ciclo {String(cycle.month).padStart(2, "0")}/{cycle.year}</h2>
        </div>
        <StatusBadge status={cycle.status} />
      </div>

      <div className="bg-white rounded-xl border">
        <div className="px-5 py-4 border-b">
          <h3 className="font-semibold">Metas por Categoria</h3>
          <p className="text-xs text-gray-400">Soma das metas dos vendedores abaixo do seu escopo</p>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="px-5 py-3">Categoria</th>
              <th className="px-5 py-3 text-right">Total kg</th>
              <th className="px-5 py-3 text-right">Vendedores</th>
              <th className="px-5 py-3 text-right">Produtos</th>
              <th className="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {summaries.map((s) => (
              <tr key={s.category_id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-5 py-3 font-medium">{s.category_name}</td>
                <td className="px-5 py-3 text-right">{Number(s.total_kg).toLocaleString("pt-BR")}</td>
                <td className="px-5 py-3 text-right">{s.sellers_count}</td>
                <td className="px-5 py-3 text-right">{s.products_count}</td>
                <td className="px-5 py-3">
                  {nodeId && (
                    <Link
                      href={`/workspace?cycle_id=${cycleId}&category_id=${s.category_id}&source_node_id=${nodeId}`}
                      className="text-blue-600 hover:underline text-sm"
                    >Distribuir</Link>
                  )}
                </td>
              </tr>
            ))}
            {summaries.length === 0 && (
              <tr><td colSpan={5} className="px-5 py-8 text-center text-gray-400">Nenhuma meta distribuida ainda</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
