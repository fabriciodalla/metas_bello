"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Shell from "@/components/Shell";
import { api, GoalCycle, NodeDashboard } from "@/lib/api";

interface Props {
  title: string;
  subordinateLabel: string;
}

export default function DistributorPanel({ title, subordinateLabel }: Props) {
  const [cycles, setCycles] = useState<GoalCycle[]>([]);
  const [selectedCycle, setSelectedCycle] = useState<number | null>(null);
  const [data, setData] = useState<NodeDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCycles().then((c) => {
      setCycles(c);
      if (c.length > 0) setSelectedCycle(c[0].id);
    });
  }, []);

  useEffect(() => {
    if (selectedCycle) {
      setLoading(true);
      api.getNodeDashboard(selectedCycle)
        .then(setData)
        .catch(() => setData(null))
        .finally(() => setLoading(false));
    }
  }, [selectedCycle]);

  const totalReceived = data?.categories.reduce((s, c) => s + Number(c.received_kg), 0) || 0;
  const totalDistributed = data?.categories.reduce((s, c) => s + Number(c.distributed_kg), 0) || 0;
  const totalRemaining = data?.categories.reduce((s, c) => s + Number(c.remaining_kg), 0) || 0;
  const allDistributed = data?.categories.length ? data.categories.every((c) => c.is_fully_distributed) : false;

  return (
    <Shell>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold">{title}</h2>
          {data && (
            <p className="text-sm text-gray-500">
              {data.node_name} — {data.level_name} — Ciclo {data.cycle_label}
            </p>
          )}
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Ciclo</label>
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
        </div>
      </div>

      {loading && !data && (
        <div className="bg-white rounded-xl border p-8 text-center text-gray-400">
          Carregando...
        </div>
      )}

      {!loading && !data && (
        <div className="bg-white rounded-xl border p-8 text-center text-gray-400">
          Nenhuma meta recebida para este ciclo.
        </div>
      )}

      {data && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-xl border p-4">
              <p className="text-xs text-gray-500 mb-1">Total Recebido</p>
              <p className="text-2xl font-bold">{totalReceived.toLocaleString("pt-BR")} kg</p>
            </div>
            <div className="bg-white rounded-xl border p-4">
              <p className="text-xs text-gray-500 mb-1">Total Distribuido</p>
              <p className="text-2xl font-bold">{totalDistributed.toLocaleString("pt-BR")} kg</p>
            </div>
            <div className={`rounded-xl border p-4 ${allDistributed ? "bg-green-50 border-green-200" : totalRemaining > 0 ? "bg-yellow-50 border-yellow-200" : "bg-white"}`}>
              <p className="text-xs text-gray-500 mb-1">Restante</p>
              <p className={`text-2xl font-bold ${allDistributed ? "text-green-600" : totalRemaining > 0 ? "text-yellow-600" : ""}`}>
                {totalRemaining.toLocaleString("pt-BR")} kg
              </p>
            </div>
          </div>

          {/* Categories table */}
          <div className="bg-white rounded-xl border mb-6">
            <div className="px-5 py-4 border-b">
              <h3 className="font-semibold">Metas por Grupo</h3>
              <p className="text-xs text-gray-400">Metas recebidas e status da distribuicao por grupo</p>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b bg-gray-50">
                  <th className="px-5 py-3">Grupo</th>
                  <th className="px-5 py-3 text-right">Recebido (kg)</th>
                  <th className="px-5 py-3 text-right">Distribuido (kg)</th>
                  <th className="px-5 py-3 text-right">Restante (kg)</th>
                  <th className="px-5 py-3 text-center">Status</th>
                  <th className="px-5 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {data.categories.map((cat) => {
                  const received = Number(cat.received_kg);
                  const distributed = Number(cat.distributed_kg);
                  const remaining = Number(cat.remaining_kg);
                  const pct = received > 0 ? Math.round((distributed / received) * 100) : 0;
                  return (
                    <tr key={cat.category_id} className="border-b last:border-0 hover:bg-gray-50">
                      <td className="px-5 py-3 font-medium">{cat.category_name}</td>
                      <td className="px-5 py-3 text-right">{received.toLocaleString("pt-BR")}</td>
                      <td className="px-5 py-3 text-right">{distributed.toLocaleString("pt-BR")}</td>
                      <td className="px-5 py-3 text-right">
                        <span className={remaining === 0 ? "text-green-600" : "text-yellow-600"}>
                          {remaining.toLocaleString("pt-BR")}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-center">
                        {cat.is_fully_distributed ? (
                          <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                            100%
                          </span>
                        ) : pct > 0 ? (
                          <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-700">
                            {pct}%
                          </span>
                        ) : (
                          <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500">
                            Pendente
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <Link
                          href={`/workspace?cycle_id=${data.cycle_id}&category_id=${cat.category_id}&source_node_id=${data.node_id}`}
                          className="text-blue-600 hover:underline text-sm"
                        >
                          Distribuir
                        </Link>
                      </td>
                    </tr>
                  );
                })}
                {data.categories.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-5 py-8 text-center text-gray-400">
                      Nenhuma meta recebida neste ciclo
                    </td>
                  </tr>
                )}
              </tbody>
              {data.categories.length > 0 && (
                <tfoot>
                  <tr className="border-t-2 font-semibold">
                    <td className="px-5 py-3">TOTAL</td>
                    <td className="px-5 py-3 text-right">{totalReceived.toLocaleString("pt-BR")}</td>
                    <td className="px-5 py-3 text-right">{totalDistributed.toLocaleString("pt-BR")}</td>
                    <td className="px-5 py-3 text-right">
                      <span className={totalRemaining === 0 ? "text-green-600" : "text-yellow-600"}>
                        {totalRemaining.toLocaleString("pt-BR")}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-center">
                      {allDistributed ? (
                        <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
                          Completo
                        </span>
                      ) : (
                        <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-700">
                          Em andamento
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3"></td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>

          {/* Subordinates table */}
          <div className="bg-white rounded-xl border">
            <div className="px-5 py-4 border-b">
              <h3 className="font-semibold">{subordinateLabel}</h3>
              <p className="text-xs text-gray-400">
                Status de recebimento e distribuicao dos subordinados diretos
              </p>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b bg-gray-50">
                  <th className="px-5 py-3">Nome</th>
                  <th className="px-5 py-3">Nivel</th>
                  <th className="px-5 py-3 text-right">Recebido (kg)</th>
                  <th className="px-5 py-3 text-right">Distribuido (kg)</th>
                  <th className="px-5 py-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.subordinates.map((sub) => {
                  const subReceived = Number(sub.total_received_kg);
                  const subDistributed = Number(sub.total_distributed_kg);
                  return (
                    <tr key={sub.node_id} className="border-b last:border-0 hover:bg-gray-50">
                      <td className="px-5 py-3 font-medium">{sub.node_name}</td>
                      <td className="px-5 py-3 text-gray-500 text-xs">{sub.level_name}</td>
                      <td className="px-5 py-3 text-right">
                        {subReceived > 0
                          ? subReceived.toLocaleString("pt-BR")
                          : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-5 py-3 text-right">
                        {subDistributed > 0
                          ? subDistributed.toLocaleString("pt-BR")
                          : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-5 py-3 text-center">
                        {sub.has_distributed ? (
                          <span className="inline-block w-2.5 h-2.5 rounded-full bg-green-500" title="Distribuiu" />
                        ) : subReceived > 0 ? (
                          <span className="inline-block w-2.5 h-2.5 rounded-full bg-yellow-400" title="Recebeu, nao distribuiu" />
                        ) : (
                          <span className="inline-block w-2.5 h-2.5 rounded-full bg-gray-300" title="Aguardando" />
                        )}
                      </td>
                    </tr>
                  );
                })}
                {data.subordinates.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-5 py-8 text-center text-gray-400">
                      Nenhum subordinado ativo
                    </td>
                  </tr>
                )}
              </tbody>
              {data.subordinates.length > 0 && (
                <tfoot>
                  <tr className="border-t font-medium text-xs text-gray-500">
                    <td className="px-5 py-3" colSpan={2}>
                      {data.subordinates.length} {subordinateLabel.toLowerCase()}
                    </td>
                    <td className="px-5 py-3 text-right">
                      {data.subordinates.reduce((s, sub) => s + Number(sub.total_received_kg), 0).toLocaleString("pt-BR")}
                    </td>
                    <td className="px-5 py-3 text-right">
                      {data.subordinates.reduce((s, sub) => s + Number(sub.total_distributed_kg), 0).toLocaleString("pt-BR")}
                    </td>
                    <td className="px-5 py-3 text-center">
                      <span className="text-xs">
                        {data.subordinates.filter((s) => s.has_distributed).length}/{data.subordinates.length}
                      </span>
                    </td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </>
      )}
    </Shell>
  );
}
