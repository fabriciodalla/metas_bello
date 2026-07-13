"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Shell from "@/components/Shell";
import { api, Workspace, SuggestionResult, SuggestionItem } from "@/lib/api";

interface EditableItem extends SuggestionItem {
  edited_kg: number;
}

export default function WorkspacePage() {
  return (
    <Suspense fallback={<Shell><p className="text-gray-400">Carregando...</p></Shell>}>
      <WorkspaceContent />
    </Suspense>
  );
}

function WorkspaceContent() {
  const searchParams = useSearchParams();
  const cycleId = Number(searchParams.get("cycle_id") || 0);
  const categoryId = Number(searchParams.get("category_id") || 0);
  const sourceNodeId = Number(searchParams.get("source_node_id") || 0);

  const [ws, setWs] = useState<Workspace | null>(null);
  const [engine, setEngine] = useState("base_distribution");
  const [startMonth, setStartMonth] = useState("");
  const [endMonth, setEndMonth] = useState("");
  const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [confirming, setConfirming] = useState(false);

  // Suggestion / editable state
  const [editItems, setEditItems] = useState<EditableItem[]>([]);
  const [budget, setBudget] = useState(0);
  const [showSuggestion, setShowSuggestion] = useState(false);

  useEffect(() => {
    if (cycleId && categoryId && sourceNodeId) load();
  }, [cycleId, categoryId, sourceNodeId]);

  async function load() {
    setMsg(null);
    const data = await api.getWorkspace(cycleId, categoryId, sourceNodeId);
    setWs(data);
  }

  // ── Engine ─────────────────────────────────────

  async function handleSuggest() {
    setMsg(null);
    try {
      const res = await api.suggest(cycleId, categoryId, sourceNodeId, engine, startMonth, endMonth);
      const items: EditableItem[] = res.items.map((i) => ({
        ...i,
        edited_kg: Number(i.suggested_kg),
      }));
      setEditItems(items);
      setBudget(Number(res.total_kg));
      setShowSuggestion(true);
    } catch (e: any) {
      setMsg({ type: "err", text: e.message });
    }
  }

  // ── Editable table helpers ─────────────────────

  const editedTotal = editItems.reduce((s, i) => s + i.edited_kg, 0);
  const delta = Math.round((budget - editedTotal) * 100) / 100;
  const isBalanced = Math.abs(delta) < 0.5;

  function handleEditKg(index: number, value: number) {
    setEditItems((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], edited_kg: Math.max(0, Math.round(value)) };
      return next;
    });
  }

  function handleRedistributeRemainder() {
    if (editItems.length === 0) return;
    const currentTotal = editItems.reduce((s, i) => s + i.edited_kg, 0);
    const remainder = Math.round(budget - currentTotal);
    if (remainder === 0) return;

    // Distribute proportionally based on current edited values
    const totalEdited = editItems.reduce((s, i) => s + Math.max(i.edited_kg, 1), 0);
    let distributed = 0;
    const parts: number[] = editItems.map((item) => {
      const share = Math.max(item.edited_kg, 1) / totalEdited;
      const extra = Math.floor(remainder * share);
      distributed += extra;
      return extra;
    });

    // Assign leftover to first items
    let leftover = remainder - distributed;
    for (let i = 0; leftover !== 0 && i < parts.length; i++) {
      const add = leftover > 0 ? 1 : -1;
      if (editItems[i].edited_kg + parts[i] + add >= 0) {
        parts[i] += add;
        leftover -= add;
      }
    }

    setEditItems((prev) =>
      prev.map((item, i) => ({
        ...item,
        edited_kg: Math.max(0, item.edited_kg + parts[i]),
      }))
    );
  }

  function handleResetToSuggested() {
    setEditItems((prev) =>
      prev.map((item) => ({ ...item, edited_kg: Number(item.suggested_kg) }))
    );
  }

  async function handleApply() {
    if (!isBalanced) {
      setMsg({ type: "err", text: `A soma (${editedTotal}) nao bate com a meta (${budget}). Diferenca: ${delta} kg` });
      return;
    }
    setMsg(null);
    try {
      const items = editItems.map((i) => ({
        destination_node_id: i.destination_node_id,
        quantity_kg: i.edited_kg,
        ...(i.product_id != null ? { product_id: i.product_id } : {}),
      }));
      await api.bulkDistribute(cycleId, categoryId, sourceNodeId, items);
      setShowSuggestion(false);
      setEditItems([]);
      await load();
      setMsg({ type: "ok", text: "Distribuicao aplicada com sucesso" });
    } catch (e: any) {
      setMsg({ type: "err", text: e.message });
    }
  }

  // ── Confirm ────────────────────────────────────

  async function handleConfirm() {
    setConfirming(true);
    setMsg(null);
    try {
      const res = await api.confirmDistributions(cycleId, categoryId, sourceNodeId);
      await load();
      setMsg({
        type: "ok",
        text: `${res.confirmed} distribuicoes confirmadas (${res.total_kg} kg). ${res.seller_goals_created} metas de vendedor gravadas.`,
      });
    } catch (e: any) {
      setMsg({ type: "err", text: e.message });
    } finally {
      setConfirming(false);
    }
  }

  async function handleDelete(distId: number) {
    try {
      await api.deleteDistribution(distId);
      await load();
    } catch (e: any) {
      setMsg({ type: "err", text: e.message });
    }
  }

  // ── Render ─────────────────────────────────────

  if (!cycleId || !categoryId || !sourceNodeId) {
    return (
      <Shell>
        <h2 className="text-2xl font-bold mb-4">Distribuir Metas</h2>
        <div className="bg-white rounded-xl border p-8 text-center text-gray-400">
          Acesse pelo detalhe do ciclo para abrir o workspace de distribuicao.
        </div>
      </Shell>
    );
  }

  if (!ws)
    return (
      <Shell>
        <p className="text-gray-400">Carregando workspace...</p>
      </Shell>
    );

  const hasOnlyDrafts =
    ws.items.length > 0 && ws.items.every((i) => i.status === "RASCUNHO");

  // Group suggestion items by product for product-level display
  const productGroups: Record<string, EditableItem[]> = {};
  if (ws.is_product_level && editItems.length > 0) {
    for (const item of editItems) {
      const key = item.product_name || "(sem produto)";
      if (!productGroups[key]) productGroups[key] = [];
      productGroups[key].push(item);
    }
  }

  return (
    <Shell>
      <div className="mb-6">
        <p className="text-sm text-gray-400">{ws.source_level}</p>
        <h2 className="text-2xl font-bold">
          {ws.source_name} — {ws.category_name}
        </h2>
        <p className="text-xs text-gray-400 mt-1">
          {ws.is_product_level
            ? "Distribuicao por PRODUTO"
            : "Distribuicao por GRUPO"}
        </p>
      </div>

      {msg && (
        <div
          className={`mb-4 p-3 rounded-lg text-sm ${
            msg.type === "ok"
              ? "bg-green-50 text-green-700 border border-green-200"
              : "bg-red-50 text-red-700 border border-red-200"
          }`}
        >
          {msg.text}
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Recebido</p>
          <p className="text-xl font-bold">
            {Number(ws.received_kg).toLocaleString("pt-BR")} kg
          </p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-500">Distribuido</p>
          <p className="text-xl font-bold">
            {Number(ws.distributed_kg).toLocaleString("pt-BR")} kg
          </p>
        </div>
        <div
          className={`rounded-xl border p-4 ${
            ws.can_confirm
              ? "bg-green-50 border-green-200"
              : "bg-red-50 border-red-200"
          }`}
        >
          <p className="text-xs text-gray-500">Restante</p>
          <p
            className={`text-xl font-bold ${
              ws.can_confirm ? "text-green-600" : "text-red-600"
            }`}
          >
            {Number(ws.remaining_kg).toLocaleString("pt-BR")} kg
          </p>
        </div>
      </div>

      {/* Current distribution lines */}
      <div className="bg-white rounded-xl border mb-6">
        <div className="px-5 py-4 border-b">
          <h3 className="font-semibold">Distribuicoes</h3>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="px-5 py-3">Destino</th>
              {ws.is_product_level && <th className="px-5 py-3">Produto</th>}
              <th className="px-5 py-3 text-right">Kg</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {ws.items.map((d) => (
              <tr key={d.id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-5 py-3 font-medium">{d.destination_name}</td>
                {ws.is_product_level && (
                  <td className="px-5 py-3 text-gray-500">{d.product_name}</td>
                )}
                <td className="px-5 py-3 text-right">
                  {Number(d.quantity_kg).toLocaleString("pt-BR")}
                </td>
                <td className="px-5 py-3">
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      d.status === "CONFIRMADA"
                        ? "bg-green-100 text-green-700"
                        : "bg-yellow-100 text-yellow-700"
                    }`}
                  >
                    {d.status === "CONFIRMADA" ? "Confirmada" : "Rascunho"}
                  </span>
                </td>
                <td className="px-5 py-3">
                  {d.status === "RASCUNHO" && (
                    <button
                      onClick={() => handleDelete(d.id)}
                      className="text-xs text-red-500 hover:underline"
                    >
                      remover
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {ws.items.length === 0 && (
              <tr>
                <td
                  colSpan={ws.is_product_level ? 5 : 4}
                  className="px-5 py-8 text-center text-gray-400"
                >
                  Nenhuma distribuicao ainda
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* ── Engine: calcular + editar ─────────────── */}
      <div className="bg-white rounded-xl border p-5 mb-6">
        <h3 className="font-semibold mb-3">Motor de Calculo</h3>
        <div className="flex items-end gap-3 flex-wrap">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Motor</label>
            <select
              value={engine}
              onChange={(e) => setEngine(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm"
            >
              <option value="base_distribution">
                Proporcional (Base)
              </option>
              <option value="portfolio">Carteira + Historico</option>
              <option value="equal">Igualitario</option>
              <option value="previous_cycle">Ciclo Anterior</option>
            </select>
          </div>
          {engine === "portfolio" && (
            <>
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Mes inicial
                </label>
                <input
                  type="month"
                  value={startMonth}
                  onChange={(e) => setStartMonth(e.target.value)}
                  className="border rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Mes final
                </label>
                <input
                  type="month"
                  value={endMonth}
                  onChange={(e) => setEndMonth(e.target.value)}
                  className="border rounded-lg px-3 py-2 text-sm"
                />
              </div>
            </>
          )}
          <button
            onClick={handleSuggest}
            className="bg-purple-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-purple-700"
          >
            Calcular
          </button>
        </div>

        {/* ── Editable suggestion table ────────── */}
        {showSuggestion && editItems.length > 0 && (
          <div className="mt-5">
            {/* Budget bar */}
            <div
              className={`flex items-center justify-between p-3 rounded-lg mb-4 ${
                isBalanced
                  ? "bg-green-50 border border-green-200"
                  : "bg-red-50 border border-red-200"
              }`}
            >
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium">
                  Meta: {budget.toLocaleString("pt-BR")} kg
                </span>
                <span className="text-sm">
                  Distribuido: {editedTotal.toLocaleString("pt-BR")} kg
                </span>
              </div>
              <div className="flex items-center gap-3">
                {!isBalanced && (
                  <span
                    className={`text-sm font-bold ${
                      delta > 0 ? "text-red-600" : "text-orange-600"
                    }`}
                  >
                    {delta > 0
                      ? `Faltam ${delta.toLocaleString("pt-BR")} kg`
                      : `Excede ${Math.abs(delta).toLocaleString("pt-BR")} kg`}
                  </span>
                )}
                {isBalanced && (
                  <span className="text-sm font-bold text-green-600">
                    Balanceado
                  </span>
                )}
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex gap-2 mb-4">
              <button
                onClick={handleResetToSuggested}
                className="text-xs text-gray-500 border rounded px-3 py-1.5 hover:bg-gray-50"
              >
                Resetar para sugestao
              </button>
              {!isBalanced && (
                <button
                  onClick={handleRedistributeRemainder}
                  className="text-xs text-purple-600 border border-purple-200 rounded px-3 py-1.5 hover:bg-purple-50"
                >
                  Redistribuir sobra proporcionalmente
                </button>
              )}
            </div>

            {/* Table — grouped by product if product_level */}
            {ws.is_product_level && Object.keys(productGroups).length > 0 ? (
              Object.entries(productGroups).map(([prodName, items]) => {
                const groupTotal = items.reduce((s, i) => s + i.edited_kg, 0);
                const groupSuggested = items.reduce(
                  (s, i) => s + Number(i.suggested_kg),
                  0
                );
                return (
                  <div key={prodName} className="mb-4">
                    <div className="flex items-center justify-between px-2 py-1.5 bg-gray-50 rounded-t border border-b-0">
                      <span className="text-xs font-semibold text-gray-600 uppercase">
                        {prodName}
                      </span>
                      <span className="text-xs text-gray-500">
                        Subtotal: {groupTotal.toLocaleString("pt-BR")} kg
                        {groupTotal !== groupSuggested && (
                          <span className="text-orange-500 ml-1">
                            (sugerido: {groupSuggested.toLocaleString("pt-BR")})
                          </span>
                        )}
                      </span>
                    </div>
                    <table className="w-full text-sm border rounded-b">
                      <thead>
                        <tr className="text-left text-gray-500 border-b bg-gray-50">
                          <th className="px-4 py-2">Destino</th>
                          <th className="px-4 py-2 text-right w-28">
                            Sugerido
                          </th>
                          <th className="px-4 py-2 text-right w-36">
                            Kg (editavel)
                          </th>
                          <th className="px-4 py-2 text-right w-20">%</th>
                        </tr>
                      </thead>
                      <tbody>
                        {items.map((item) => {
                          const globalIdx = editItems.indexOf(item);
                          const changed =
                            item.edited_kg !== Number(item.suggested_kg);
                          return (
                            <tr
                              key={globalIdx}
                              className="border-b last:border-0 hover:bg-gray-50"
                            >
                              <td className="px-4 py-2 font-medium">
                                {item.destination_name}
                              </td>
                              <td className="px-4 py-2 text-right text-gray-400">
                                {Number(item.suggested_kg).toLocaleString(
                                  "pt-BR"
                                )}
                              </td>
                              <td className="px-4 py-2 text-right">
                                <input
                                  type="number"
                                  min={0}
                                  value={item.edited_kg}
                                  onChange={(e) =>
                                    handleEditKg(
                                      globalIdx,
                                      Number(e.target.value)
                                    )
                                  }
                                  className={`w-24 text-right border rounded px-2 py-1 text-sm ${
                                    changed
                                      ? "border-orange-400 bg-orange-50 font-semibold"
                                      : "border-gray-200"
                                  }`}
                                />
                              </td>
                              <td className="px-4 py-2 text-right text-gray-500">
                                {Number(item.percent).toFixed(1)}%
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                );
              })
            ) : (
              <table className="w-full text-sm border rounded">
                <thead>
                  <tr className="text-left text-gray-500 border-b bg-gray-50">
                    <th className="px-4 py-2">Destino</th>
                    <th className="px-4 py-2 text-right w-28">Sugerido</th>
                    <th className="px-4 py-2 text-right w-36">
                      Kg (editavel)
                    </th>
                    <th className="px-4 py-2 text-right w-20">%</th>
                  </tr>
                </thead>
                <tbody>
                  {editItems.map((item, idx) => {
                    const changed =
                      item.edited_kg !== Number(item.suggested_kg);
                    return (
                      <tr
                        key={idx}
                        className="border-b last:border-0 hover:bg-gray-50"
                      >
                        <td className="px-4 py-2 font-medium">
                          {item.destination_name}
                        </td>
                        <td className="px-4 py-2 text-right text-gray-400">
                          {Number(item.suggested_kg).toLocaleString("pt-BR")}
                        </td>
                        <td className="px-4 py-2 text-right">
                          <input
                            type="number"
                            min={0}
                            value={item.edited_kg}
                            onChange={(e) =>
                              handleEditKg(idx, Number(e.target.value))
                            }
                            className={`w-24 text-right border rounded px-2 py-1 text-sm ${
                              changed
                                ? "border-orange-400 bg-orange-50 font-semibold"
                                : "border-gray-200"
                            }`}
                          />
                        </td>
                        <td className="px-4 py-2 text-right text-gray-500">
                          {Number(item.percent).toFixed(1)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr className="border-t font-semibold">
                    <td className="px-4 py-2">Total</td>
                    <td className="px-4 py-2 text-right text-gray-400">
                      {budget.toLocaleString("pt-BR")}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <span
                        className={
                          isBalanced ? "text-green-600" : "text-red-600"
                        }
                      >
                        {editedTotal.toLocaleString("pt-BR")}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right text-gray-500">
                      100%
                    </td>
                  </tr>
                </tfoot>
              </table>
            )}

            {/* Apply button */}
            <div className="flex items-center gap-3 mt-4">
              <button
                onClick={handleApply}
                disabled={!isBalanced}
                className={`px-5 py-2 rounded-lg text-sm font-medium ${
                  isBalanced
                    ? "bg-green-600 text-white hover:bg-green-700"
                    : "bg-gray-200 text-gray-400 cursor-not-allowed"
                }`}
              >
                Aplicar distribuicao
              </button>
              <button
                onClick={() => {
                  setShowSuggestion(false);
                  setEditItems([]);
                }}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Cancelar
              </button>
              {!isBalanced && (
                <span className="text-xs text-red-500">
                  Ajuste os valores para que a soma bata com a meta de{" "}
                  {budget.toLocaleString("pt-BR")} kg
                </span>
              )}
            </div>
          </div>
        )}

        {showSuggestion && editItems.length === 0 && (
          <p className="mt-4 text-sm text-gray-400">
            Nenhuma sugestao gerada. Verifique se ha dados historicos e
            distribuicao confirmada para este no.
          </p>
        )}
      </div>

      {/* Confirm button */}
      {hasOnlyDrafts && (
        <div className="flex justify-end">
          <button
            onClick={handleConfirm}
            disabled={!ws.can_confirm || confirming}
            className={`px-6 py-3 rounded-lg text-sm font-medium ${
              ws.can_confirm
                ? "bg-blue-600 text-white hover:bg-blue-700"
                : "bg-gray-200 text-gray-400 cursor-not-allowed"
            }`}
          >
            {confirming
              ? "Confirmando..."
              : ws.can_confirm
              ? "Confirmar distribuicao"
              : `Faltam ${Number(ws.remaining_kg).toLocaleString("pt-BR")} kg`}
          </button>
        </div>
      )}
    </Shell>
  );
}
