"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, GoalCycle, Holiday, WorkingDaysPreview } from "@/lib/api";

const NATIONAL_HOLIDAYS: Record<string, string> = {
  "01-01": "Confraternizacao Universal",
  "04-21": "Tiradentes",
  "05-01": "Dia do Trabalho",
  "09-07": "Independencia do Brasil",
  "10-12": "Nossa Sra. Aparecida",
  "11-02": "Finados",
  "11-15": "Proclamacao da Republica",
  "12-25": "Natal",
};

export default function DiasUteisPage() {
  const [tab, setTab] = useState<"feriados" | "dias-uteis">("dias-uteis");
  const [cycles, setCycles] = useState<GoalCycle[]>([]);
  const [selectedCycle, setSelectedCycle] = useState<number | null>(null);

  // Working days state
  const [preview, setPreview] = useState<WorkingDaysPreview | null>(null);
  const [editValues, setEditValues] = useState<Record<string, number>>({});
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");

  // Holidays state
  const [holidays, setHolidays] = useState<Holiday[]>([]);
  const [holidayYear, setHolidayYear] = useState(new Date().getFullYear());
  const [newDate, setNewDate] = useState("");
  const [newName, setNewName] = useState("");
  const [addingError, setAddingError] = useState("");
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    api.getCycles().then((c) => {
      setCycles(c);
      if (c.length > 0) setSelectedCycle(c[0].id);
    });
  }, []);

  useEffect(() => {
    if (selectedCycle) loadPreview(selectedCycle);
  }, [selectedCycle]);

  useEffect(() => {
    loadHolidays();
  }, [holidayYear]);

  async function loadPreview(cycleId: number) {
    const p = await api.getWorkingDaysPreview(cycleId);
    setPreview(p);
    const vals: Record<string, number> = {};
    for (const m of p.months) {
      vals[`${m.year}-${m.month}`] = m.confirmed_days ?? m.calculated_days;
    }
    setEditValues(vals);
    setSaveMsg("");
  }

  async function loadHolidays() {
    setHolidays(await api.getHolidays(holidayYear));
  }

  async function handleSaveWorkingDays() {
    if (!preview) return;
    setSaving(true);
    setSaveMsg("");
    try {
      const months = preview.months.map((m) => ({
        year: m.year,
        month: m.month,
        confirmed_days: editValues[`${m.year}-${m.month}`] ?? m.effective_days,
      }));
      const updated = await api.updateWorkingDays(preview.cycle_id, months);
      setPreview(updated);
      setSaveMsg("Dias uteis confirmados com sucesso!");
    } catch (err: any) {
      setSaveMsg(`Erro: ${err.message}`);
    } finally {
      setSaving(false);
    }
  }

  async function handleAddHoliday(e: React.FormEvent) {
    e.preventDefault();
    setAddingError("");
    if (!newDate || !newName) {
      setAddingError("Preencha data e nome");
      return;
    }
    try {
      await api.createHoliday({ holiday_date: newDate, name: newName });
      setNewDate("");
      setNewName("");
      await loadHolidays();
      if (selectedCycle) await loadPreview(selectedCycle);
    } catch (err: any) {
      setAddingError(err.message);
    }
  }

  async function handleDeleteHoliday(id: number) {
    await api.deleteHoliday(id);
    await loadHolidays();
    if (selectedCycle) await loadPreview(selectedCycle);
  }

  async function handleGenerateNational() {
    setGenerating(true);
    try {
      const items = Object.entries(NATIONAL_HOLIDAYS).map(([mmdd, name]) => ({
        holiday_date: `${holidayYear}-${mmdd}`,
        name,
      }));
      await api.bulkCreateHolidays(items);
      await loadHolidays();
      if (selectedCycle) await loadPreview(selectedCycle);
    } finally {
      setGenerating(false);
    }
  }

  function dayOfWeekLabel(dateStr: string) {
    const d = new Date(dateStr + "T12:00:00");
    return d.toLocaleDateString("pt-BR", { weekday: "short" });
  }

  return (
    <Shell>
      <h2 className="text-2xl font-bold mb-1">Dias Uteis e Feriados</h2>
      <p className="text-sm text-gray-500 mb-6">
        Gerencie feriados e confirme os dias uteis para o calculo de metas.
      </p>

      {/* Tabs */}
      <div className="flex gap-1 mb-6">
        <button
          onClick={() => setTab("dias-uteis")}
          className={`px-4 py-2 rounded-t-lg text-sm font-medium border border-b-0 ${
            tab === "dias-uteis"
              ? "bg-white text-blue-700 border-gray-200"
              : "bg-gray-50 text-gray-500 border-transparent hover:bg-gray-100"
          }`}
        >
          Dias Uteis por Ciclo
        </button>
        <button
          onClick={() => setTab("feriados")}
          className={`px-4 py-2 rounded-t-lg text-sm font-medium border border-b-0 ${
            tab === "feriados"
              ? "bg-white text-blue-700 border-gray-200"
              : "bg-gray-50 text-gray-500 border-transparent hover:bg-gray-100"
          }`}
        >
          Feriados
        </button>
      </div>

      {/* ── Tab: Dias Úteis ─────────────────────── */}
      {tab === "dias-uteis" && (
        <div className="bg-white rounded-xl border p-5">
          <div className="flex items-center gap-4 mb-5">
            <label className="text-sm font-medium text-gray-700">Ciclo:</label>
            <select
              value={selectedCycle ?? ""}
              onChange={(e) => setSelectedCycle(Number(e.target.value))}
              className="border rounded-lg px-3 py-2 text-sm"
            >
              {cycles.map((c) => (
                <option key={c.id} value={c.id}>
                  {String(c.month).padStart(2, "0")}/{c.year} — {c.status}
                </option>
              ))}
            </select>
          </div>

          {preview && (
            <>
              <p className="text-xs text-gray-400 mb-3">
                Mês alvo: {String(preview.target_month).padStart(2, "0")}/{preview.target_year}.
                Os 3 meses anteriores sao usados para calcular a media diaria no motor de distribuicao.
              </p>
              <table className="w-full text-sm mb-4">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="px-4 py-2">Mes</th>
                    <th className="px-4 py-2 text-center">Dias na Semana</th>
                    <th className="px-4 py-2 text-center">Feriados</th>
                    <th className="px-4 py-2 text-center">Calculado</th>
                    <th className="px-4 py-2 text-center">Confirmado</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.months.map((m) => {
                    const key = `${m.year}-${m.month}`;
                    const changed =
                      editValues[key] !== undefined &&
                      editValues[key] !== m.calculated_days;
                    return (
                      <tr
                        key={key}
                        className={`border-b last:border-0 ${
                          m.is_target ? "bg-blue-50" : ""
                        }`}
                      >
                        <td className="px-4 py-3 font-medium">
                          {m.label}
                          {m.is_target && (
                            <span className="ml-2 text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                              MES ALVO
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">{m.weekdays}</td>
                        <td className="px-4 py-3 text-center">
                          {m.holidays_count > 0 ? (
                            <span className="text-orange-600 font-medium">
                              {m.holidays_count}
                            </span>
                          ) : (
                            <span className="text-gray-300">0</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center text-gray-500">
                          {m.calculated_days}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <input
                            type="number"
                            min={1}
                            max={31}
                            value={editValues[key] ?? m.calculated_days}
                            onChange={(e) =>
                              setEditValues((prev) => ({
                                ...prev,
                                [key]: Number(e.target.value),
                              }))
                            }
                            className={`w-16 text-center border rounded px-2 py-1 text-sm ${
                              changed
                                ? "border-orange-400 bg-orange-50"
                                : "border-gray-200"
                            }`}
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                <tfoot>
                  <tr className="border-t font-medium">
                    <td className="px-4 py-3">Total 3 meses anteriores</td>
                    <td className="px-4 py-3 text-center">
                      {preview.months
                        .filter((m) => !m.is_target)
                        .reduce((s, m) => s + m.weekdays, 0)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {preview.months
                        .filter((m) => !m.is_target)
                        .reduce((s, m) => s + m.holidays_count, 0)}
                    </td>
                    <td className="px-4 py-3 text-center text-gray-500">
                      {preview.months
                        .filter((m) => !m.is_target)
                        .reduce((s, m) => s + m.calculated_days, 0)}
                    </td>
                    <td className="px-4 py-3 text-center font-semibold">
                      {preview.months
                        .filter((m) => !m.is_target)
                        .reduce(
                          (s, m) =>
                            s +
                            (editValues[`${m.year}-${m.month}`] ??
                              m.calculated_days),
                          0
                        )}
                    </td>
                  </tr>
                </tfoot>
              </table>

              <div className="flex items-center gap-3">
                <button
                  onClick={handleSaveWorkingDays}
                  disabled={saving}
                  className="bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                >
                  {saving ? "Salvando..." : "Confirmar Dias Uteis"}
                </button>
                {saveMsg && (
                  <span
                    className={`text-sm ${
                      saveMsg.startsWith("Erro")
                        ? "text-red-600"
                        : "text-green-600"
                    }`}
                  >
                    {saveMsg}
                  </span>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Tab: Feriados ──────────────────────── */}
      {tab === "feriados" && (
        <div className="bg-white rounded-xl border p-5">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-700">Ano:</label>
              <select
                value={holidayYear}
                onChange={(e) => setHolidayYear(Number(e.target.value))}
                className="border rounded-lg px-3 py-2 text-sm"
              >
                {[2025, 2026, 2027, 2028].map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={handleGenerateNational}
              disabled={generating}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {generating
                ? "Gerando..."
                : `Gerar Feriados Nacionais ${holidayYear}`}
            </button>
          </div>

          {/* Add holiday form */}
          <form
            onSubmit={handleAddHoliday}
            className="flex items-end gap-3 mb-5 pb-5 border-b"
          >
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Data
              </label>
              <input
                type="date"
                value={newDate}
                onChange={(e) => setNewDate(e.target.value)}
                className="border rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Nome do feriado
              </label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Ex: Carnaval, Corpus Christi..."
                className="border rounded-lg px-3 py-2 text-sm w-full"
              />
            </div>
            <button
              type="submit"
              className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700"
            >
              Adicionar
            </button>
            {addingError && (
              <span className="text-sm text-red-600">{addingError}</span>
            )}
          </form>

          {/* Holidays table */}
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="px-4 py-2">Data</th>
                <th className="px-4 py-2">Dia</th>
                <th className="px-4 py-2">Nome</th>
                <th className="px-4 py-2 text-center">Cai em dia util?</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {holidays.map((h) => {
                const d = new Date(h.holiday_date + "T12:00:00");
                const isWeekday = d.getDay() > 0 && d.getDay() < 6;
                return (
                  <tr
                    key={h.id}
                    className="border-b last:border-0 hover:bg-gray-50"
                  >
                    <td className="px-4 py-2 font-medium">
                      {new Date(h.holiday_date + "T12:00:00").toLocaleDateString(
                        "pt-BR"
                      )}
                    </td>
                    <td className="px-4 py-2 text-gray-500">
                      {dayOfWeekLabel(h.holiday_date)}
                    </td>
                    <td className="px-4 py-2">{h.name}</td>
                    <td className="px-4 py-2 text-center">
                      {isWeekday ? (
                        <span className="text-orange-600 font-medium">Sim</span>
                      ) : (
                        <span className="text-gray-300">Nao</span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <button
                        onClick={() => handleDeleteHoliday(h.id)}
                        className="text-red-500 hover:text-red-700 text-xs"
                      >
                        Remover
                      </button>
                    </td>
                  </tr>
                );
              })}
              {holidays.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-8 text-center text-gray-400"
                  >
                    Nenhum feriado cadastrado para {holidayYear}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          {holidays.length > 0 && (
            <p className="text-xs text-gray-400 mt-3">
              Total em dias uteis:{" "}
              <span className="font-medium text-gray-600">
                {holidays.filter((h) => {
                  const d = new Date(h.holiday_date + "T12:00:00");
                  return d.getDay() > 0 && d.getDay() < 6;
                }).length}
              </span>{" "}
              feriados que reduzem dias uteis
            </p>
          )}
        </div>
      )}
    </Shell>
  );
}
