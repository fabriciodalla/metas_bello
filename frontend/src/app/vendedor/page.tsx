"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, GoalCycle, SellerGoal } from "@/lib/api";

export default function VendedorPage() {
  const [cycles, setCycles] = useState<GoalCycle[]>([]);
  const [selectedCycle, setSelectedCycle] = useState<number | null>(null);
  const [goals, setGoals] = useState<SellerGoal[]>([]);
  const [loading, setLoading] = useState(true);
  const [sellerName, setSellerName] = useState("");
  const [nodeId, setNodeId] = useState<number | null>(null);

  useEffect(() => {
    api.me().then((u) => {
      setSellerName(u.full_name || u.username);
      setNodeId(u.scope_node_id);
    });
    api.getCycles().then((c) => {
      setCycles(c);
      if (c.length > 0) setSelectedCycle(c[0].id);
    });
  }, []);

  useEffect(() => {
    if (selectedCycle && nodeId) {
      setLoading(true);
      api.getSellerGoals(selectedCycle, { seller_node_id: nodeId })
        .then(setGoals)
        .finally(() => setLoading(false));
    }
  }, [selectedCycle, nodeId]);

  const totalKg = goals.reduce((s, g) => s + Number(g.quantity_kg), 0);

  const byCategory: Record<string, SellerGoal[]> = {};
  for (const g of goals) {
    if (!byCategory[g.category_name]) byCategory[g.category_name] = [];
    byCategory[g.category_name].push(g);
  }

  return (
    <Shell>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold">Minhas Metas</h2>
          <p className="text-sm text-gray-500">{sellerName}</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-xs text-gray-500">{goals.length} metas</p>
            <p className="text-xl font-bold text-blue-700">
              {totalKg.toLocaleString("pt-BR")} kg
            </p>
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
      </div>

      {loading ? (
        <div className="bg-white rounded-xl border p-8 text-center text-gray-400">
          Carregando...
        </div>
      ) : goals.length === 0 ? (
        <div className="bg-white rounded-xl border p-8 text-center text-gray-400">
          Nenhuma meta atribuida para este ciclo.
        </div>
      ) : (
        Object.entries(byCategory).map(([catName, catGoals]) => {
          const catTotal = catGoals.reduce((s, g) => s + Number(g.quantity_kg), 0);
          return (
            <div key={catName} className="bg-white rounded-xl border mb-4">
              <div className="px-5 py-4 border-b flex justify-between items-center bg-blue-50 rounded-t-xl">
                <div>
                  <h3 className="font-semibold">{catName}</h3>
                  <p className="text-xs text-gray-500">{catGoals.length} produtos</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-500">Subtotal</p>
                  <p className="text-lg font-bold">{catTotal.toLocaleString("pt-BR")} kg</p>
                </div>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="px-5 py-3">Produto</th>
                    <th className="px-5 py-3 text-right">Meta (kg)</th>
                    <th className="px-5 py-3 text-right">% do Grupo</th>
                  </tr>
                </thead>
                <tbody>
                  {catGoals.map((g) => {
                    const kg = Number(g.quantity_kg);
                    const pct = catTotal > 0 ? ((kg / catTotal) * 100).toFixed(1) : "0.0";
                    return (
                      <tr key={g.id} className="border-b last:border-0 hover:bg-gray-50">
                        <td className="px-5 py-2 font-medium">{g.product_name}</td>
                        <td className="px-5 py-2 text-right font-medium">
                          {kg.toLocaleString("pt-BR")}
                        </td>
                        <td className="px-5 py-2 text-right text-gray-500">{pct}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
        })
      )}

      {/* Total geral */}
      {goals.length > 0 && (
        <div className="bg-blue-50 rounded-xl border border-blue-200 p-5 flex justify-between items-center">
          <div>
            <p className="text-sm font-semibold text-blue-700">Meta Total do Ciclo</p>
            <p className="text-xs text-gray-500">
              {Object.keys(byCategory).length} grupos, {goals.length} produtos
            </p>
          </div>
          <p className="text-2xl font-bold text-blue-700">
            {totalKg.toLocaleString("pt-BR")} kg
          </p>
        </div>
      )}
    </Shell>
  );
}
