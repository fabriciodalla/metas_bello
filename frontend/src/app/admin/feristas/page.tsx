"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import { api, Substitution } from "@/lib/api";

export default function FeristasAdminPage() {
  const [subs, setSubs] = useState<Substitution[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getSubstitutions().then(setSubs).finally(() => setLoading(false));
  }, []);

  return (
    <Shell>
      <h2 className="text-2xl font-bold mb-4">Feristas</h2>
      <p className="text-sm text-gray-500 mb-6">Vendedores substitutos cobrindo ferias de titulares.</p>

      <div className="bg-white rounded-xl border">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="px-4 py-3">Titular</th>
              <th className="px-4 py-3">Ferista</th>
              <th className="px-4 py-3">Inicio</th>
              <th className="px-4 py-3">Fim</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">Carregando...</td></tr>
            ) : subs.length === 0 ? (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">Nenhum ferista cadastrado</td></tr>
            ) : subs.map((s) => (
              <tr key={s.id} className="border-b last:border-0 hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{s.titular_name}</td>
                <td className="px-4 py-2">{s.substitute_name}</td>
                <td className="px-4 py-2 text-gray-500">{s.starts_on}</td>
                <td className="px-4 py-2 text-gray-500">{s.ends_on}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
