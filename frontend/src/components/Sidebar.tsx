"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  href: string;
  label: string;
  roles?: string[];
}

interface NavSection {
  title: string;
  roles?: string[];
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: "Comercial",
    items: [
      { href: "/", label: "Dashboard" },
      { href: "/gerencia", label: "Painel Gerencial", roles: ["ADMINISTRADOR", "GERENTE"] },
      { href: "/coordenacao-regional", label: "Painel Regional", roles: ["ADMINISTRADOR", "COORDENADOR_REGIONAL"] },
      { href: "/coordenacao-local", label: "Painel Local", roles: ["ADMINISTRADOR", "COORDENADOR_LOCAL"] },
      { href: "/supervisao", label: "Painel Supervisor", roles: ["ADMINISTRADOR", "SUPERVISOR"] },
      { href: "/vendedor", label: "Minhas Metas", roles: ["VENDEDOR"] },
      { href: "/ciclos", label: "Ciclos", roles: ["ADMINISTRADOR", "GERENTE", "COORDENADOR_REGIONAL", "COORDENADOR_LOCAL"] },
      { href: "/workspace", label: "Distribuir Metas", roles: ["ADMINISTRADOR", "GERENTE", "COORDENADOR_REGIONAL", "COORDENADOR_LOCAL", "SUPERVISOR"] },
      { href: "/metas", label: "Metas Vendedores" },
    ],
  },
  {
    title: "Administracao",
    roles: ["ADMINISTRADOR"],
    items: [
      { href: "/admin/hierarquia", label: "Hierarquia" },
      { href: "/admin/produtos", label: "Produtos" },
      { href: "/admin/usuarios", label: "Usuarios" },
      { href: "/admin/feristas", label: "Feristas" },
      { href: "/admin/dias-uteis", label: "Dias Uteis" },
    ],
  },
];

export default function Sidebar({ role }: { role?: string }) {
  const pathname = usePathname();
  const userRole = role || "";

  const visibleSections = NAV_SECTIONS
    .filter((s) => !s.roles || s.roles.includes(userRole))
    .map((s) => ({
      ...s,
      items: s.items.filter((i) => !i.roles || i.roles.includes(userRole)),
    }))
    .filter((s) => s.items.length > 0);

  return (
    <aside className="w-56 bg-white border-r border-gray-200 min-h-screen p-4 flex flex-col">
      <div className="mb-8">
        <h1 className="text-lg font-bold text-blue-700">Metas Bello</h1>
        <p className="text-[10px] text-gray-400">v3.0</p>
      </div>
      {visibleSections.map((section) => (
        <div key={section.title} className="mb-6">
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2 px-3">
            {section.title}
          </p>
          <nav className="space-y-0.5">
            {section.items.map((item) => {
              const active =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block px-3 py-1.5 rounded text-sm transition-colors ${
                    active
                      ? "bg-blue-50 text-blue-700 font-medium"
                      : "text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      ))}
    </aside>
  );
}
