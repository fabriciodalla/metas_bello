"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Shell from "@/components/Shell";
import StatusBadge from "@/components/StatusBadge";
import { api, GoalCycle } from "@/lib/api";

export default function CiclosPage() {
  const [cycles, setCycles] = useState<GoalCycle[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [month, setMonth] = useState(new Date().getMonth() + 2 > 12 ? 1 : new Date().getMonth() + 2);
  const [year, setYear] = useState(new Date().getMonth() + 2 > 12 ? new Date().getFullYear() + 1 : new Date().getFullYear());
  const [error, setError] = useState("");

  useEffect(() => { load(); }, []);

  async function load() { setCycles(await api.getCycles()); }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try { await api.createCycle(month, year); setShowForm(false); await load(); }
    catch (err: any) { setError(err.message); }
  }

  return (
    <Shell>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Ciclos de Meta</h2>
        <button onClick={() => setShowForm(!showForm)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          Novo ciclo
        </button>
      </div>

      {showForm && (
        <div className="bg-white rounded-xl border p-5 mb-6">
          <form onSubmit={handleCreate} className="flex items-end gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Mes</label>
              <select value={month} onChange={(e) => setMonth(Number(e.target.value))} className="border rounded-lg px-3 py-2 text-sm">
                {Array.from({ length: 12 }, (_, i) => <option key={i+1} value={i+1}>{String(i+1).padStart(2,"0")}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Ano</label>
              <input type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} className="border rounded-lg px-3 py-2 text-sm w-24" />
            </div>
            <button type="submit" className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700">Criar</button>
            {error && <p className="text-sm text-red-600">{error}</p>}
          </form>
        </div>
      )}

      <div className="bg-white rounded-xl border">
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
            {cycles.map((c) => (
              <tr key={c.id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-5 py-3 font-medium">{String(c.month).padStart(2,"0")}/{c.year}</td>
                <td className="px-5 py-3 text-right">{Number(c.total_kg).toLocaleString("pt-BR")}</td>
                <td className="px-5 py-3 text-right">{c.sellers_count}</td>
                <td className="px-5 py-3"><StatusBadge status={c.status} /></td>
                <td className="px-5 py-3">
                  <Link href={`/ciclos/${c.id}`} className="text-blue-600 hover:underline text-sm">Detalhar</Link>
                </td>
              </tr>
            ))}
            {cycles.length === 0 && <tr><td colSpan={5} className="px-5 py-8 text-center text-gray-400">Nenhum ciclo</td></tr>}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
