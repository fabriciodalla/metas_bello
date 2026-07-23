import { useLocation } from "react-router-dom";
import type { User } from "../../api/types";
import { distribuirMetasLabel } from "../distribuicaoLabels";
import { UserMenu } from "./UserMenu";

const ADMIN_LABELS: Record<string, string> = {
  "visao-geral": "Visão Geral",
  gestao: "Gestão",
  metas: "Metas",
  pendencias: "Pendências",
  "pre-processamento": "Pré-processamento",
  dashboard: "Dashboard",
};

const NIVEL_LABELS: Record<string, string> = {
  "visao-geral": "Visão Geral",
  "meta-gerencial": "Meta Gerencial",
  "distribuir-produtos": "Distribuir Produtos",
  "meta-supervisor": "Meta Supervisor",
  "meta-vendedor": "Meta Vendedor",
  pendencias: "Pendências",
};

const NIVEL_SUBTITLES: Record<string, string> = {
  "distribuir-produtos": "Distribua os produtos para os usuários coordenadores locais e regionais",
};

const ACOMPANHAMENTO_LABELS: Record<string, string> = {
  "acumulado-vendas": "Acumulado Vendas",
  "acumulado-clientes": "Acumulado Clientes",
  "metas-gerais": "Acompanhamento Metas Gerais",
};

const FINALIZACAO_LABELS: Record<string, string> = {
  fechamento: "Tabela de Fechamento",
};

function usePageTitle(user: User) {
  const location = useLocation();
  const segments = location.pathname.split("/").filter(Boolean);

  switch (segments[0]) {
    case "admin":
      return ADMIN_LABELS[segments[1]];
    case "distribuicao":
      // "distribuir" muda de rótulo conforme quem está logado (ver distribuicaoLabels.ts) —
      // as demais rotas do nível têm rótulo fixo.
      return segments[1] === "distribuir" ? distribuirMetasLabel(user.hierarchy_nodes) : NIVEL_LABELS[segments[1]];
    case "acompanhamento":
      return ACOMPANHAMENTO_LABELS[segments[1]];
    case "finalizacao":
      return FINALIZACAO_LABELS[segments[1]];
    default:
      return undefined;
  }
}

function usePageSubtitle() {
  const location = useLocation();
  const segments = location.pathname.split("/").filter(Boolean);
  if (segments[0] !== "distribuicao") return undefined;
  return NIVEL_SUBTITLES[segments[1]];
}

export function Topbar({ user, onLogout }: { user: User; onLogout: () => void }) {
  const title = usePageTitle(user);
  const subtitle = usePageSubtitle();

  return (
    <header className="topbar">
      <div className="topbar-heading">
        <h1 className="topbar-title">{title ?? "Bello Vendas"}</h1>
        {subtitle && <p className="topbar-subtitle">{subtitle}</p>}
      </div>
      <UserMenu user={user} onLogout={onLogout} />
    </header>
  );
}
