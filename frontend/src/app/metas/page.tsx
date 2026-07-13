"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, GoalCycle, SellerGoal } from "@/lib/api";

export default function MetasPage() {
  const [cycles, setCycles] = useState<GoalCycle[]>([]);
  const [selectedCycle, setSelectedCycle] = useState<number | null>(null);
  const [goals, setGoals] = useState<SellerGoal[]>([]);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    api.getCycles().then((c) => {
      setCycles(c);
      if (c.length > 0) {
        setSelectedCycle(c[0].id);
      }
    });
  }, []);

  useEffect(() => {
    if (selectedCycle) {
      api.getSellerGoals(selectedCycle).then(setGoals);
    }
  }, [selectedCycle]);

  const filtered = goals.filter((g) =>
    !filter ||
    g.seller_name.toLowerCase().includes(filter.toLowerCase()) ||
    g.product_name.toLowerCase().includes(filter.toLowerCase()) ||
    g.category_name.toLowerCase().includes(filter.toLowerCase())
  );

  const totalKg = filtered.reduce((s, g) => s + Number(g.quantity_kg), 0);
  const uniqueSellers = new Set(filtered.map((g) => g.seller_node_id)).size;

  return (
    <Shell>
      <h2 className="text-2xl font-bold mb-4">Metas dos Vendedores</h2>

      <div className="flex items-center gap-4 mb-6">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Ciclo</label>
          <select
            value={selectedCycle || ""}
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
        <div className="flex-1">
          <label className="block text-xs text-gray-500 mb-1">Buscar</label>
          <input
            type="text"
            placeholder="Vendedor, produto ou categoria..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm w-full max-w-sm"
          />
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500">{uniqueSellers} vendedores, {filtered.length} metas</p>
          <p className="text-lg font-bold">{totalKg.toLocaleString("pt-BR")} kg</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="px-5 py-3">Vendedor</th>
              <th className="px-5 py-3">Categoria</th>
              <th className="px-5 py-3">Produto</th>
              <th className="px-5 py-3 text-right">Meta (kg)</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((g) => (
              <tr key={g.id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-5 py-2 font-medium">{g.seller_name}</td>
                <td className="px-5 py-2 text-gray-500">{g.category_name}</td>
                <td className="px-5 py-2">{g.product_name}</td>
                <td className="px-5 py-2 text-right font-medium">{Number(g.quantity_kg).toLocaleString("pt-BR")}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr><td colSpan={4} className="px-5 py-8 text-center text-gray-400">Nenhuma meta encontrada</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
