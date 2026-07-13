"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import {
  api,
  GoalCycle,
  DashboardData,
  CategoryTargets,
} from "@/lib/api";

export default function GerenciaPage() {
  const [cycles, setCycles] = useState<GoalCycle[]>([]);
  const [selectedCycle, setSelectedCycle] = useState<number | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const [user, setUser] = useState<{ role: string } | null>(null);
  const [gerenteNodes, setGerenteNodes] = useState<{ id: number; name: string }[]>([]);
  const [selectedNode, setSelectedNode] = useState<number | undefined>(undefined);

  // Editable state
  const [workingDays, setWorkingDays] = useState(0);
  const [metas, setMetas] = useState<Record<number, number>>({});
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  useEffect(() => {
    api.me().then((u) => {
      setUser(u);
      if (u.role === "ADMINISTRADOR") {
        api.getGerenteNodes().then((nodes) => {
          setGerenteNodes(nodes);
          if (nodes.length > 0) setSelectedNode(nodes[0].id);
        });
      }
    });
    api.getCycles().then((c) => {
      setCycles(c);
      if (c.length > 0) setSelectedCycle(c[0].id);
    });
  }, []);

  useEffect(() => {
    if (selectedCycle) loadDashboard();
  }, [selectedCycle, selectedNode]);

  async function loadDashboard() {
    if (!selectedCycle) return;
    setMsg(null);
    try {
      const d = await api.getGerenciaDashboard(selectedCycle, selectedNode);
      setData(d);
      setWorkingDays(d.targets.target_working_days);
      const m: Record<number, number> = {};
      for (const cat of d.targets.categories) {
        m[cat.category_id] =
          Number(cat.current_meta) > 0
            ? Number(cat.current_meta)
            : Number(cat.total_individual);
      }
      setMetas(m);
    } catch (e: any) {
      setMsg({ type: "err", text: e.message });
    }
  }

  function recalcMeta(cat: CategoryTargets): number {
    if (!data) return 0;
    const origWd = data.targets.target_working_days;
    if (origWd <= 0) return Number(cat.total_individual);
    return Math.round(
      (Number(cat.total_daily_avg) * workingDays)
    );
  }

  function handleWorkingDaysChange(newWd: number) {
    if (!data) return;
    const clamped = Math.max(1, Math.min(31, newWd));
    setWorkingDays(clamped);
    const m: Record<number, number> = {};
    for (const cat of data.targets.categories) {
      m[cat.category_id] = Math.round(Number(cat.total_daily_avg) * clamped);
    }
    setMetas(m);
  }

  async function handleSave() {
    if (!data || !selectedCycle) return;
    setSaving(true);
    setMsg(null);
    try {
      const items = data.targets.categories
        .filter((c) => (metas[c.category_id] || 0) > 0)
        .map((c) => ({
          category_id: c.category_id,
          budget_kg: metas[c.category_id] || 0,
        }));
      await api.setGerenciaBudget(selectedCycle, items, selectedNode);
      await loadDashboard();
      setMsg({ type: "ok", text: "Metas salvas com sucesso" });
    } catch (e: any) {
      setMsg({ type: "err", text: e.message });
    } finally {
      setSaving(false);
    }
  }

  function toggleExpand(catId: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(catId) ? next.delete(catId) : next.add(catId);
      return next;
    });
  }

  const totalMeta = Object.values(metas).reduce((s, v) => s + (v || 0), 0);

  return (
    <Shell>
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold">Painel Gerencial</h2>
          {data && (
            <p className="text-sm text-gray-500">
              {data.targets.gerente_name} — Ciclo {data.targets.cycle_label}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {user?.role === "ADMINISTRADOR" && gerenteNodes.length > 1 && (
            <div>
              <label className="block text-xs text-gray-500 mb-1">Gerente</label>
              <select
                value={selectedNode ?? ""}
                onChange={(e) => setSelectedNode(Number(e.target.value))}
                className="border rounded-lg px-3 py-2 text-sm"
              >
                {gerenteNodes.map((n) => (
                  <option key={n.id} value={n.id}>{n.name}</option>
                ))}
              </select>
            </div>
          )}
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

      {msg && (
        <div className={`mb-4 p-3 rounded-lg text-sm ${
          msg.type === "ok"
            ? "bg-green-50 text-green-700 border border-green-200"
            : "bg-red-50 text-red-700 border border-red-200"
        }`}>{msg.text}</div>
      )}

      {data && (
        <>
          {/* ── Metas por Categoria (tabela unificada) ── */}
          <div className="bg-white rounded-xl border mb-6">
            <div className="px-5 py-4 border-b flex justify-between items-center">
              <div>
                <h3 className="font-semibold">Metas por Grupo</h3>
                <p className="text-xs text-gray-400">
                  Base: media diaria dos ultimos 3 meses ({data.targets.prev_working_days} dias uteis)
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-500">Meta Total</p>
                <p className="text-xl font-bold text-blue-700">
                  {totalMeta.toLocaleString("pt-BR")} kg
                </p>
              </div>
            </div>

            <table className="w-full text-sm table-fixed">
              <colgroup>
                <col className="w-[40%]" />
                <col className="w-[20%]" />
                <col className="w-[20%]" />
                <col className="w-[20%]" />
              </colgroup>
              <thead>
                <tr className="text-left text-gray-500 border-b bg-gray-50">
                  <th className="px-5 py-3">Grupo / Subgrupo</th>
                  <th className="px-5 py-3 text-right">Meta Diaria (kg)</th>
                  <th className="px-5 py-3 text-right">Meta Individual (kg)</th>
                  <th className="px-5 py-3 text-right">Meta (kg)</th>
                </tr>
              </thead>
              <tbody>
                {data.targets.categories.flatMap((cat) => {
                  const isExpanded = expanded.has(cat.category_id);
                  const metaVal = metas[cat.category_id] || 0;
                  const rows = [];
                  rows.push(
                    <tr key={`cat-${cat.category_id}`}
                        className="border-b bg-blue-50 hover:bg-blue-100 cursor-pointer"
                        onClick={() => toggleExpand(cat.category_id)}>
                      <td className="px-5 py-3 font-semibold">
                        <span className="text-gray-400 mr-2 text-xs">
                          {isExpanded ? "▼" : "▶"}
                        </span>
                        {cat.category_name}
                        <span className="text-xs text-gray-400 ml-2">
                          ({cat.products.length} subgrupos)
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right font-semibold">
                        {Number(cat.total_daily_avg).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
                      </td>
                      <td className="px-5 py-3 text-right font-semibold text-gray-500">
                        {Number(cat.total_individual).toLocaleString("pt-BR")}
                      </td>
                      <td className="px-5 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="number"
                          min={0}
                          value={metaVal || ""}
                          onChange={(e) =>
                            setMetas((prev) => ({
                              ...prev,
                              [cat.category_id]: Math.max(0, Math.round(Number(e.target.value))),
                            }))
                          }
                          placeholder="0"
                          className={`w-28 text-right border rounded px-2 py-1.5 text-sm font-semibold ${
                            metaVal !== Number(cat.total_individual)
                              ? "border-orange-400 bg-orange-50"
                              : "border-gray-200"
                          }`}
                        />
                      </td>
                    </tr>
                  );
                  if (isExpanded) {
                    for (const p of cat.products) {
                      rows.push(
                        <tr key={`prod-${p.product_id}`} className="border-b hover:bg-gray-50">
                          <td className="px-5 py-2 pl-12 text-gray-600 text-xs">
                            {p.product_name}
                          </td>
                          <td className="px-5 py-2 text-right text-xs text-gray-500">
                            {Number(p.daily_avg).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
                          </td>
                          <td className="px-5 py-2 text-right text-xs text-gray-500">
                            {Number(p.individual_target).toLocaleString("pt-BR")}
                          </td>
                          <td className="px-5 py-2"></td>
                        </tr>
                      );
                    }
                  }
                  return rows;
                })}
              </tbody>
              <tfoot>
                <tr className="border-t-2 font-bold">
                  <td className="px-5 py-3">TOTAL GERAL</td>
                  <td className="px-5 py-3 text-right">
                    {data.targets.categories
                      .reduce((s, c) => s + Number(c.total_daily_avg), 0)
                      .toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
                  </td>
                  <td className="px-5 py-3 text-right text-gray-500">
                    {data.targets.categories
                      .reduce((s, c) => s + Number(c.total_individual), 0)
                      .toLocaleString("pt-BR")}
                  </td>
                  <td className="px-5 py-3 text-right text-blue-700 text-lg">
                    {totalMeta.toLocaleString("pt-BR")}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>

          {/* ── Dias uteis + salvar ────────────────── */}
          <div className="bg-white rounded-xl border p-5 flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">
                  Dias uteis do mes alvo
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={1}
                    max={31}
                    value={workingDays}
                    onChange={(e) => handleWorkingDaysChange(Number(e.target.value))}
                    className="w-20 text-center border rounded-lg px-3 py-2 text-sm font-semibold"
                  />
                  <span className="text-xs text-gray-400">
                    dias
                  </span>
                  {workingDays !== data.targets.target_working_days && (
                    <span className="text-xs text-orange-500">
                      (original: {data.targets.target_working_days})
                    </span>
                  )}
                </div>
              </div>
              <div className="text-xs text-gray-400 max-w-xs">
                Alterar os dias uteis recalcula a meta de todos os grupos.
                Voce tambem pode editar cada meta manualmente.
              </div>
            </div>
            <button
              onClick={handleSave}
              disabled={saving}
              className="bg-green-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {saving ? "Salvando..." : "Salvar Metas"}
            </button>
          </div>
        </>
      )}

      {!data && !msg && (
        <div className="bg-white rounded-xl border p-8 text-center text-gray-400">
          Carregando...
        </div>
      )}
    </Shell>
  );
}
