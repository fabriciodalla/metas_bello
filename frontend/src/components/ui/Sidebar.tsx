import {
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronsLeft,
  ChevronsRight,
  Eye,
  LayoutGrid,
  type LucideIcon,
  ListChecks,
  RefreshCw,
  Target,
  TrendingUp,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import type { User } from "../../api/types";
import belloBWhite from "../../assets/bello-b-white.png";
import { distribuirMetasLabel, showsDistribuirMetas } from "../distribuicaoLabels";
import { OVERVIEW_LEVELS, type Level } from "../../pages/admin/constants";

const ADMIN_NAV_ITEMS = [
  { to: "/admin/visao-geral", label: "Visão Geral", icon: Eye },
  { to: "/admin/gestao", label: "Gestão", icon: Users },
  { to: "/admin/metas", label: "Metas", icon: Target },
  { to: "/admin/pendencias", label: "Pendências", icon: ListChecks },
  { to: "/admin/pre-processamento", label: "Pré-processamento", icon: RefreshCw },
  { to: "/admin/dashboard", label: "Dashboard", icon: BarChart3 },
];

type NivelGroupItem = { to: string; label: string; hidden?: boolean };
type NivelGroup = { key: string; label: string; icon: LucideIcon; items: NivelGroupItem[] };

function useNivelGroups(user: User): NivelGroup[] {
  return useMemo(() => {
    const levels = new Set(user.hierarchy_nodes.map((n) => n.level));
    // Visão Geral e Pendências dependem do mesmo critério: só fazem sentido pra quem tem
    // subordinado que não seja folha (Vendedor) — por isso Supervisor não vê nenhuma das duas.
    const showOverview = [...levels].some((level) => OVERVIEW_LEVELS.has(level as Level));
    const showPendencias = showOverview;
    const showMetaGerencial = levels.has("GERENTE");
    const showLocalSplitFlow = levels.has("LOCAL");
    const showSupervisorSplitFlow = levels.has("SUPERVISOR");

    const groups: NivelGroup[] = [
      {
        key: "distribuicao",
        label: "Distribuição",
        icon: LayoutGrid,
        items: [
          { to: "/distribuicao/visao-geral", label: "Visão Geral", hidden: !showOverview },
          { to: "/distribuicao/meta-gerencial", label: "Meta Gerencial", hidden: !showMetaGerencial },
          {
            to: "/distribuicao/distribuir",
            label: distribuirMetasLabel(user.hierarchy_nodes),
            hidden: !showsDistribuirMetas(user.hierarchy_nodes),
          },
          { to: "/distribuicao/distribuir-produtos", label: "Distribuir Produtos", hidden: !showLocalSplitFlow },
          { to: "/distribuicao/meta-supervisor", label: "Meta Supervisor", hidden: !showLocalSplitFlow },
          { to: "/distribuicao/meta-vendedor", label: "Meta Vendedor", hidden: !showSupervisorSplitFlow },
          { to: "/distribuicao/pendencias", label: "Pendências", hidden: !showPendencias },
        ],
      },
      {
        key: "acompanhamento",
        label: "Acompanhamento",
        icon: TrendingUp,
        items: [
          { to: "/acompanhamento/acumulado-vendas", label: "Acumulado Vendas" },
          { to: "/acompanhamento/acumulado-clientes", label: "Acumulado Clientes" },
          { to: "/acompanhamento/metas-gerais", label: "Acompanhamento Metas Gerais" },
        ],
      },
      {
        key: "finalizacao",
        label: "Finalização",
        icon: CheckCircle2,
        items: [{ to: "/finalizacao/fechamento", label: "Tabela de Fechamento" }],
      },
    ];

    return groups.map((group) => ({ ...group, items: group.items.filter((item) => !item.hidden) }));
  }, [user]);
}

export function Sidebar({ user }: { user: User }) {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const nivelGroups = useNivelGroups(user);

  const activeGroupKey = nivelGroups.find((group) =>
    group.items.some((item) => location.pathname.startsWith(item.to)),
  )?.key;

  const [openGroups, setOpenGroups] = useState<Set<string>>(() => new Set(activeGroupKey ? [activeGroupKey] : []));

  useEffect(() => {
    if (!activeGroupKey) return;
    setOpenGroups((prev) => (prev.has(activeGroupKey) ? prev : new Set(prev).add(activeGroupKey)));
  }, [activeGroupKey]);

  function toggleGroup(key: string) {
    setOpenGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  return (
    <aside className={`sidebar${collapsed ? " collapsed" : ""}`}>
      <div className="sidebar-brand">
        <img src={belloBWhite} alt="Bello" className="sidebar-brand-mark" />
        <span className="sidebar-brand-text">
          Bello <span className="sidebar-brand-accent">Vendas</span>
        </span>
      </div>

      <nav className="sidebar-nav">
        {user.is_admin
          ? ADMIN_NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}>
                <Icon size={18} strokeWidth={2} />
                <span>{label}</span>
              </NavLink>
            ))
          : nivelGroups.map((group) => {
              const isOpen = openGroups.has(group.key);
              const GroupIcon = group.icon;
              return (
                <div className="sidebar-group" key={group.key}>
                  <button
                    type="button"
                    className={`sidebar-link sidebar-group-toggle${isOpen ? " open" : ""}`}
                    onClick={() => toggleGroup(group.key)}
                    aria-expanded={isOpen}
                  >
                    <GroupIcon size={18} strokeWidth={2} />
                    <span>{group.label}</span>
                    <ChevronDown size={16} strokeWidth={2} className="sidebar-group-chevron" />
                  </button>
                  {isOpen && (
                    <div className="sidebar-group-items">
                      {group.items.map(({ to, label }) => (
                        <NavLink
                          key={to}
                          to={to}
                          className={({ isActive }) => `sidebar-sublink${isActive ? " active" : ""}`}
                        >
                          <span>{label}</span>
                        </NavLink>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
      </nav>

      <button
        type="button"
        className="sidebar-toggle"
        onClick={() => setCollapsed((c) => !c)}
        aria-label={collapsed ? "Expandir menu" : "Recolher menu"}
      >
        {collapsed ? <ChevronsRight size={16} /> : <ChevronsLeft size={16} />}
      </button>
    </aside>
  );
}
