"use client";

import Shell from "@/components/Shell";

export default function UsuariosAdminPage() {
  return (
    <Shell>
      <h2 className="text-2xl font-bold mb-4">Usuarios</h2>
      <p className="text-sm text-gray-500 mb-6">Gerencie os usuarios do sistema, seus perfis e escopos.</p>

      <div className="bg-white rounded-xl border p-5">
        <p className="text-gray-400 text-center py-8">Endpoint de listagem de usuarios sera adicionado. Usuarios carregados via seed.</p>
      </div>
    </Shell>
  );
}
