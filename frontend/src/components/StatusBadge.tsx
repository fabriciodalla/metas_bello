const COLORS: Record<string, string> = {
  RASCUNHO: "bg-gray-100 text-gray-600",
  EM_DISTRIBUICAO: "bg-yellow-100 text-yellow-700",
  FECHADO: "bg-green-100 text-green-700",
  FECHADA: "bg-green-100 text-green-700",
  CANCELADO: "bg-red-100 text-red-600",
  CANCELADA: "bg-red-100 text-red-600",
  BLOQUEADA: "bg-orange-100 text-orange-700",
  ENVIADA: "bg-blue-100 text-blue-700",
};

const LABELS: Record<string, string> = {
  RASCUNHO: "Rascunho",
  EM_DISTRIBUICAO: "Em distribuicao",
  FECHADO: "Fechado",
  FECHADA: "Fechada",
  CANCELADO: "Cancelado",
  CANCELADA: "Cancelada",
  BLOQUEADA: "Bloqueada",
  ENVIADA: "Enviada",
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
        COLORS[status] || "bg-gray-100 text-gray-500"
      }`}
    >
      {LABELS[status] || status}
    </span>
  );
}
